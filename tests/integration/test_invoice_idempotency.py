import threading

from tests.conftest import register_merchant, register_recipient


def test_idempotent_replay_returns_existing_invoice_without_reprocessing(client):
    merchant_id = register_merchant(client, "AR")
    recipient_id = register_recipient(client, "AR")
    payload = {
        "entity_id": "e1",
        "amount": 100.0,
        "issuer_merchant_id": merchant_id,
        "recipient_id": recipient_id,
    }
    headers = {"Idempotency-Key": "idem-sequential-1"}

    first = client.post("/invoices", json=payload, headers=headers)
    assert first.status_code == 202
    first_id = first.json()["invoice_id"]

    second = client.post("/invoices", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["invoice_id"] == first_id

    detail = client.get(f"/invoices/{first_id}").json()
    # Only ever processed once: a second call to the provider would show up as
    # a second attempt row.
    assert len(detail["attempts"]) == 1


def test_idempotent_replay_is_safe_under_concurrent_requests(client):
    merchant_id = register_merchant(client, "AR")
    recipient_id = register_recipient(client, "AR")
    payload = {
        "entity_id": "e1",
        "amount": 100.0,
        "issuer_merchant_id": merchant_id,
        "recipient_id": recipient_id,
    }
    headers = {"Idempotency-Key": "idem-concurrent-1"}
    responses = []
    lock = threading.Lock()

    def _post():
        resp = client.post("/invoices", json=payload, headers=headers)
        with lock:
            responses.append(resp)

    threads = [threading.Thread(target=_post) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(responses) == 10
    invoice_ids = {r.json()["invoice_id"] for r in responses}
    # The DB unique constraint on idempotency_key guarantees exactly one winner,
    # regardless of how many requests race to create the same key.
    assert len(invoice_ids) == 1

    status_codes = sorted(r.status_code for r in responses)
    assert status_codes.count(202) == 1
    assert status_codes.count(200) == 9

    (invoice_id,) = invoice_ids
    detail = client.get(f"/invoices/{invoice_id}").json()
    assert len(detail["attempts"]) == 1
