from datetime import datetime
from typing import Any, Optional

from domain.interfaces.invoice_attempt_repository import InvoiceAttemptRepository
from domain.models.invoice_attempt import AttemptStatus, InvoiceAttempt
from domain.value_objects.invoice_id import InvoiceId
from infrastructure.db import SessionLocal
from infrastructure.orm.invoice_attempt_orm import InvoiceAttemptORM
from infrastructure.orm.mappers.invoice_attempt_mapper import invoice_attempt_orm_to_domain


class SqlAlchemyInvoiceAttemptRepository(InvoiceAttemptRepository):

    def record(
        self,
        invoice_id: InvoiceId,
        attempt_number: int,
        provider: str,
        request_payload: dict[str, Any],
        response_payload: Optional[dict[str, Any]],
        error_message: Optional[str],
        status: AttemptStatus,
        duration_ms: int,
        started_at: datetime,
        finished_at: datetime,
    ) -> InvoiceAttempt:
        with SessionLocal() as session:
            orm = InvoiceAttemptORM(
                invoice_id=invoice_id.value,
                attempt_number=attempt_number,
                provider=provider,
                request_payload=request_payload,
                response_payload=response_payload,
                error_message=error_message,
                status=status.value,
                duration_ms=duration_ms,
                started_at=started_at,
                finished_at=finished_at,
            )
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return invoice_attempt_orm_to_domain(orm)

    def list_by_invoice(self, invoice_id: InvoiceId) -> list[InvoiceAttempt]:
        with SessionLocal() as session:
            rows = (
                session.query(InvoiceAttemptORM)
                .filter(InvoiceAttemptORM.invoice_id == invoice_id.value)
                .order_by(InvoiceAttemptORM.attempt_number.asc())
                .all()
            )
            return [invoice_attempt_orm_to_domain(r) for r in rows]
