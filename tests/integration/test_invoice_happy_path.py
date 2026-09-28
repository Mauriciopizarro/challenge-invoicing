from tests.conftest import register_merchant, register_recipient


def test_ar_happy_path(client):
    merchant_id = register_merchant(client, "AR")
    recipient_id = register_recipient(client, "AR")
    resp = client.post(
        "/invoices",
        json={
            "entity_id": "acme",
            "amount": 150.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "happy-ar-1"},
    )
    assert resp.status_code == 202
    body = resp.json()
    # Always reflects the pre-processing snapshot (the async contract), even
    # though the test queue's is_async=False already ran the job by now.
    assert body["status"] == "pending"
    assert body["provider_used"] == "AFIP"
    assert body["external_reference"] is None

    detail = client.get(f"/invoices/{body['invoice_id']}").json()
    assert detail["status"] == "issued"
    assert detail["external_reference"] is not None
    assert detail["failure_reason"] is None
    assert detail["issuer_merchant_id"] == merchant_id
    assert detail["recipient_id"] == recipient_id
    assert detail["issuer"]["tax_id"]["id_type"] == "CUIT"
    assert len(detail["attempts"]) == 1
    assert detail["attempts"][0]["status"] == "success"
    assert detail["attempts"][0]["provider"] == "AFIP"


def test_br_happy_path(client):
    merchant_id = register_merchant(client, "BR")
    recipient_id = register_recipient(client, "BR")
    resp = client.post(
        "/invoices",
        json={
            "entity_id": "acme-br",
            "amount": 200.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "happy-br-1"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["provider_used"] == "NFe"

    detail = client.get(f"/invoices/{body['invoice_id']}").json()
    assert detail["status"] == "issued"
    assert detail["external_reference"].startswith("NFE-")


def test_invalid_amount_rejected(client):
    merchant_id = register_merchant(client, "AR")
    recipient_id = register_recipient(client, "AR")
    resp = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": -5.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "invalid-amount-1"},
    )
    assert resp.status_code == 422


def test_missing_idempotency_key_rejected(client):
    merchant_id = register_merchant(client, "AR")
    recipient_id = register_recipient(client, "AR")
    resp = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 10.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
    )
    assert resp.status_code == 422


def test_unknown_issuer_merchant_returns_404(client):
    recipient_id = register_recipient(client, "AR")
    resp = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 10.0,
            "issuer_merchant_id": "00000000-0000-0000-0000-000000000000",
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "unknown-merchant-1"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "merchant_not_found"


def test_unknown_recipient_returns_404(client):
    merchant_id = register_merchant(client, "AR")
    resp = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 10.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": "00000000-0000-0000-0000-000000000000",
        },
        headers={"Idempotency-Key": "unknown-recipient-1"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "recipient_not_found"


def test_get_unknown_invoice_returns_404(client):
    resp = client.get("/invoices/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "invoice_not_found"
