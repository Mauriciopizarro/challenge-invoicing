from datetime import datetime
from typing import Any

from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from domain.exceptions.provider_errors import ProviderTransientError
from domain.interfaces.invoice_attempt_repository import InvoiceAttemptRepository
from domain.interfaces.invoice_provider import InvoiceProvider, ProviderRequest, ProviderResponse
from domain.models.invoice_attempt import AttemptStatus
from domain.value_objects.invoice_id import InvoiceId


def _serialize_request(request: ProviderRequest) -> dict[str, Any]:
    # Decimal isn't JSON-serializable (needed for the JSONB audit column), so the
    # amount is stored as a string rather than a native number.
    return {
        "entity_id": request.entity_id,
        "amount": str(request.amount),
        "currency": request.currency,
        "country_code": request.country_code,
    }


class ProviderInvoker:
    def __init__(self, attempt_repo: InvoiceAttemptRepository):
        self.attempt_repo = attempt_repo

    def invoke_with_retry(
        self, provider: InvoiceProvider, request: ProviderRequest, invoice_id: InvoiceId
    ) -> ProviderResponse:
        request_payload = _serialize_request(request)
        attempt_count = 0

        # Logging happens inside this wrapped call, not in tenacity's before/after
        # hooks: `after` only fires when tenacity has decided to retry, never on
        # the terminal attempt (success or permanent failure), so an earlier
        # hook-based version silently dropped the audit row for both of those.
        def _call() -> ProviderResponse:
            nonlocal attempt_count
            attempt_count += 1
            started_at = datetime.utcnow()
            try:
                response = provider.send_invoice(request)
            except Exception as exc:
                finished_at = datetime.utcnow()
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                status = (
                    AttemptStatus.FAILED_TRANSIENT
                    if isinstance(exc, ProviderTransientError)
                    else AttemptStatus.FAILED_PERMANENT
                )
                self.attempt_repo.record(
                    invoice_id=invoice_id,
                    attempt_number=attempt_count,
                    provider=provider.name,
                    request_payload=request_payload,
                    response_payload=None,
                    error_message=str(exc),
                    status=status,
                    duration_ms=duration_ms,
                    started_at=started_at,
                    finished_at=finished_at,
                )
                raise

            finished_at = datetime.utcnow()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            self.attempt_repo.record(
                invoice_id=invoice_id,
                attempt_number=attempt_count,
                provider=provider.name,
                request_payload=request_payload,
                response_payload=response.raw_payload,
                error_message=None,
                status=AttemptStatus.SUCCESS,
                duration_ms=duration_ms,
                started_at=started_at,
                finished_at=finished_at,
            )
            return response

        retryer = Retrying(
            stop=stop_after_attempt(provider.max_retries),
            wait=wait_exponential(multiplier=provider.backoff_base, max=provider.backoff_max),
            retry=retry_if_exception_type(ProviderTransientError),
            reraise=True,
        )
        return retryer(_call)
