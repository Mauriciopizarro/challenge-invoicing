from domain.models.invoice_attempt import AttemptStatus, InvoiceAttempt
from domain.value_objects.invoice_id import InvoiceId
from infrastructure.orm.invoice_attempt_orm import InvoiceAttemptORM


def invoice_attempt_orm_to_domain(orm: InvoiceAttemptORM) -> InvoiceAttempt:
    return InvoiceAttempt(
        id=orm.id,
        invoice_id=InvoiceId(value=orm.invoice_id),
        attempt_number=orm.attempt_number,
        provider=orm.provider,
        request_payload=orm.request_payload,
        response_payload=orm.response_payload,
        error_message=orm.error_message,
        status=AttemptStatus(orm.status),
        duration_ms=orm.duration_ms,
        started_at=orm.started_at,
        finished_at=orm.finished_at,
    )
