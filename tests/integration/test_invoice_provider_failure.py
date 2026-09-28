from domain.exceptions.provider_errors import ProviderPermanentError, ProviderTransientError
from infrastructure.providers.ar_provider import ArgentinaInvoiceProvider
from tests.conftest import corrupt_extra_fields, register_merchant, register_recipient
from tests.fakes.fake_provider import AlwaysFailFault


def test_permanent_provider_failure_marks_invoice_failed(client, set_fixed_provider):
    merchant_id = register_merchant(client, "AR")
    recipient_id = register_recipient(client, "AR")
    provider = ArgentinaInvoiceProvider(
        fault_injector=AlwaysFailFault(lambda: ProviderPermanentError("payload rejected by AFIP"))
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
        headers={"Idempotency-Key": "permanent-fail-1"},
    )
    assert resp.status_code == 202
    invoice_id = resp.json()["invoice_id"]

    detail = client.get(f"/invoices/{invoice_id}").json()
    assert detail["status"] == "failed"
    assert detail["failure_reason"] == "payload rejected by AFIP"

    # A permanent error must never be retried: exactly one attempt logged.
    assert len(detail["attempts"]) == 1
    assert detail["attempts"][0]["status"] == "failed_permanent"


def test_transient_provider_failure_exhausts_retries_and_marks_failed(client, set_fixed_provider):
    merchant_id = register_merchant(client, "AR")
    recipient_id = register_recipient(client, "AR")
    provider = ArgentinaInvoiceProvider(
        fault_injector=AlwaysFailFault(lambda: ProviderTransientError("AFIP timeout"))
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
        headers={"Idempotency-Key": "transient-exhausted-1"},
    )
    invoice_id = resp.json()["invoice_id"]

    detail = client.get(f"/invoices/{invoice_id}").json()
    assert detail["status"] == "failed"
    assert detail["failure_reason"] == "AFIP timeout"

    # AR's max_retries is 3: exactly 3 attempts, all transient failures.
    assert len(detail["attempts"]) == ArgentinaInvoiceProvider.max_retries
    assert all(a["status"] == "failed_transient" for a in detail["attempts"])


def test_recipient_missing_required_fiscal_field_marks_invoice_failed(client):
    # Registration already blocks this, so simulate drift after a valid one.
    merchant_id = register_merchant(client, "AR")
    recipient_id = register_recipient(client, "AR")
    corrupt_extra_fields("recipients", recipient_id)

    resp = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 10.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "recipient-missing-field-1"},
    )
    assert resp.status_code == 202  # validated async, not at submission time
    invoice_id = resp.json()["invoice_id"]

    detail = client.get(f"/invoices/{invoice_id}").json()
    assert detail["status"] == "failed"
    assert "condicion_iva" in detail["failure_reason"]
    assert "AFIP" in detail["failure_reason"]
    assert len(detail["attempts"]) == 1
    assert detail["attempts"][0]["status"] == "failed_permanent"


def test_recipient_tax_id_type_mismatch_marks_invoice_failed(client):
    merchant_id = register_merchant(client, "AR")
    # A recipient registered under MX (RFC, not CUIT) is perfectly valid on
    # its own — the mismatch only shows up when it's used for an AR invoice.
    recipient_id = register_recipient(client, "MX")

    resp = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 10.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "recipient-wrong-tax-id-1"},
    )
    invoice_id = resp.json()["invoice_id"]

    detail = client.get(f"/invoices/{invoice_id}").json()
    assert detail["status"] == "failed"
    assert "tax id type" in detail["failure_reason"]
