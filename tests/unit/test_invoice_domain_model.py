from decimal import Decimal
from uuid import uuid4

import pytest

from domain.models.invoice import Invoice, InvoiceStatus
from domain.value_objects.merchant_id import MerchantId
from domain.value_objects.recipient_id import RecipientId
from tests.fakes.fiscal_data import fiscal_party


def _make_invoice(**overrides):
    defaults = dict(
        entity_id="e1",
        amount=Decimal("100.00"),
        currency="ARS",
        country_code="AR",
        provider_used="AFIP",
        idempotency_key="key-1",
        issuer_merchant_id=MerchantId(value=uuid4()),
        issuer=fiscal_party("AR"),
        recipient_id=RecipientId(value=uuid4()),
        recipient=fiscal_party("AR"),
    )
    defaults.update(overrides)
    return Invoice.create(**defaults)


def test_create_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        _make_invoice(amount=Decimal("0"))
    with pytest.raises(ValueError):
        _make_invoice(amount=Decimal("-1"))


def test_create_defaults_to_pending():
    invoice = _make_invoice()
    assert invoice.status == InvoiceStatus.PENDING
    assert invoice.external_reference is None
    assert invoice.failure_reason is None


def test_happy_state_transitions():
    invoice = _make_invoice()
    processing = invoice.start_processing()
    assert processing.status == InvoiceStatus.PROCESSING

    issued = processing.mark_issued("ext-ref-1")
    assert issued.status == InvoiceStatus.ISSUED
    assert issued.external_reference == "ext-ref-1"


def test_failed_transition():
    invoice = _make_invoice().start_processing()
    failed = invoice.mark_failed("provider rejected")
    assert failed.status == InvoiceStatus.FAILED
    assert failed.failure_reason == "provider rejected"


def test_cannot_start_processing_twice():
    invoice = _make_invoice().start_processing()
    with pytest.raises(ValueError):
        invoice.start_processing()


def test_cannot_mark_issued_without_processing():
    invoice = _make_invoice()
    with pytest.raises(ValueError):
        invoice.mark_issued("ext-ref-1")


def test_cannot_mark_failed_without_processing():
    invoice = _make_invoice()
    with pytest.raises(ValueError):
        invoice.mark_failed("some reason")


def test_invoice_is_immutable():
    invoice = _make_invoice()
    with pytest.raises(Exception):
        invoice.status = InvoiceStatus.ISSUED
