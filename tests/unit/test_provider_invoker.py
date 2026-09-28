from decimal import Decimal
from uuid import uuid4

import pytest

from application.services.provider_invoker import ProviderInvoker
from domain.exceptions.provider_errors import ProviderPermanentError, ProviderTransientError
from domain.interfaces.invoice_attempt_repository import InvoiceAttemptRepository
from domain.interfaces.invoice_provider import InvoiceProvider, ProviderRequest, ProviderResponse
from domain.models.invoice_attempt import AttemptStatus, InvoiceAttempt
from domain.value_objects.invoice_id import InvoiceId
from tests.fakes.fiscal_data import fiscal_party


class InMemoryAttemptRepo(InvoiceAttemptRepository):
    def __init__(self):
        self.rows: list[InvoiceAttempt] = []

    def record(self, **kwargs):
        attempt = InvoiceAttempt(**kwargs)
        self.rows.append(attempt)
        return attempt

    def list_by_invoice(self, invoice_id):
        return [r for r in self.rows if r.invoice_id.value == invoice_id.value]


class FlakyProvider(InvoiceProvider):
    name = "TEST"
    timeout_seconds = 1.0
    max_retries = 3
    backoff_base = 0.01
    backoff_max = 0.05

    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.calls = 0

    def send_invoice(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ProviderTransientError("flaky")
        return ProviderResponse(external_reference="ref-123", raw_payload={"ok": True})


class PermanentlyFailingProvider(InvoiceProvider):
    name = "TEST-PERMANENT"
    max_retries = 3
    backoff_base = 0.01
    backoff_max = 0.05

    def send_invoice(self, request: ProviderRequest) -> ProviderResponse:
        raise ProviderPermanentError("nope")


@pytest.fixture
def request_and_id():
    req = ProviderRequest(
        entity_id="e1",
        amount=Decimal("10.00"),
        currency="ARS",
        country_code="AR",
        issuer=fiscal_party("AR"),
        recipient=fiscal_party("AR"),
    )
    return req, InvoiceId(value=uuid4())


def test_recovers_after_transient_failures_logs_each_attempt(request_and_id):
    request, invoice_id = request_and_id
    repo = InMemoryAttemptRepo()
    invoker = ProviderInvoker(repo)

    response = invoker.invoke_with_retry(FlakyProvider(fail_times=2), request, invoice_id)

    assert response.external_reference == "ref-123"
    assert [r.status for r in repo.rows] == [
        AttemptStatus.FAILED_TRANSIENT,
        AttemptStatus.FAILED_TRANSIENT,
        AttemptStatus.SUCCESS,
    ]
    assert [r.attempt_number for r in repo.rows] == [1, 2, 3]


def test_exhausts_retries_and_reraises(request_and_id):
    request, invoice_id = request_and_id
    repo = InMemoryAttemptRepo()
    invoker = ProviderInvoker(repo)

    with pytest.raises(ProviderTransientError):
        invoker.invoke_with_retry(FlakyProvider(fail_times=99), request, invoice_id)

    assert len(repo.rows) == FlakyProvider.max_retries
    assert all(r.status == AttemptStatus.FAILED_TRANSIENT for r in repo.rows)


def test_permanent_error_is_never_retried(request_and_id):
    request, invoice_id = request_and_id
    repo = InMemoryAttemptRepo()
    invoker = ProviderInvoker(repo)

    with pytest.raises(ProviderPermanentError):
        invoker.invoke_with_retry(PermanentlyFailingProvider(), request, invoice_id)

    assert len(repo.rows) == 1
    assert repo.rows[0].status == AttemptStatus.FAILED_PERMANENT
