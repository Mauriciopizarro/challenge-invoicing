from rq import Queue, SimpleWorker

import main
from domain.exceptions.provider_errors import ProviderTransientError
from infrastructure.providers.ar_provider import ArgentinaInvoiceProvider
from tests.conftest import register_merchant, register_recipient
from tests.fakes.fake_provider import FlakyFault


def test_recovers_after_transient_failures(client, set_fixed_provider):
    merchant_id = register_merchant(client, "AR")
    recipient_id = register_recipient(client, "AR")
    provider = ArgentinaInvoiceProvider(
        fault_injector=FlakyFault(2, lambda: ProviderTransientError("AFIP hiccup"))
    )
    set_fixed_provider(provider)

    resp = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 10.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "recovers-1"},
    )
    invoice_id = resp.json()["invoice_id"]

    detail = client.get(f"/invoices/{invoice_id}").json()
    assert detail["status"] == "issued"
    assert detail["external_reference"] is not None

    statuses = [a["status"] for a in detail["attempts"]]
    assert statuses == ["failed_transient", "failed_transient", "success"]


def test_post_returns_pending_before_worker_processes_it(fake_redis):
    # Proves the real async contract with a genuinely async queue: POST
    # responds before any provider call, and the invoice only reaches its
    # terminal state once a worker drains the queue.
    main.container.redis_conn.override(fake_redis)
    async_queue = Queue(name="invoices", connection=fake_redis, is_async=True)
    main.container.invoice_queue.override(async_queue)

    from starlette.testclient import TestClient

    with TestClient(main.app) as client:
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
            headers={"Idempotency-Key": "async-contract-1"},
        )
        assert resp.status_code == 202
        invoice_id = resp.json()["invoice_id"]

        # Nothing has run yet: still pending, no attempts.
        detail = client.get(f"/invoices/{invoice_id}").json()
        assert detail["status"] == "pending"
        assert detail["attempts"] == []

        # Drain the queue exactly once (burst=True returns as soon as it's
        # empty instead of blocking forever) — this is the same SimpleWorker
        # class the real worker container runs.
        SimpleWorker([async_queue], connection=fake_redis).work(burst=True)

        detail = client.get(f"/invoices/{invoice_id}").json()
        assert detail["status"] == "issued"
        assert len(detail["attempts"]) == 1

    main.container.reset_override()
