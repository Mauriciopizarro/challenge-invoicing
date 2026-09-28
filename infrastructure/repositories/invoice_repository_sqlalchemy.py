from typing import Optional

from sqlalchemy.exc import IntegrityError

from domain.exceptions.idempotency_conflict import IdempotencyConflict
from domain.interfaces.invoice_repository import InvoiceRepository
from domain.models.invoice import Invoice
from domain.value_objects.invoice_id import InvoiceId
from infrastructure.db import SessionLocal
from infrastructure.orm.invoice_orm import InvoiceORM
from infrastructure.orm.mappers.invoice_mapper import invoice_domain_to_orm, invoice_orm_to_domain


class SqlAlchemyInvoiceRepository(InvoiceRepository):

    def save_new(self, invoice: Invoice) -> Invoice:
        with SessionLocal() as session:
            orm = invoice_domain_to_orm(invoice)
            session.add(orm)
            try:
                session.commit()
            except IntegrityError:
                # Safety comes from the DB unique constraint (correct under
                # concurrency); this just translates it into a domain exception.
                session.rollback()
                raise IdempotencyConflict(invoice.idempotency_key) from None
            session.refresh(orm)
            return invoice_orm_to_domain(orm)

    def get_by_id(self, invoice_id: InvoiceId) -> Optional[Invoice]:
        with SessionLocal() as session:
            orm = session.get(InvoiceORM, invoice_id.value)
            return invoice_orm_to_domain(orm) if orm else None

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Invoice]:
        with SessionLocal() as session:
            orm = (
                session.query(InvoiceORM)
                .filter(InvoiceORM.idempotency_key == idempotency_key)
                .one_or_none()
            )
            return invoice_orm_to_domain(orm) if orm else None

    def update(self, invoice: Invoice) -> Invoice:
        with SessionLocal() as session:
            orm = session.get(InvoiceORM, invoice.id.value)
            if orm is None:
                raise ValueError(f"Cannot update invoice '{invoice.id}': not found")

            orm.status = invoice.status.value
            orm.external_reference = invoice.external_reference
            orm.failure_reason = invoice.failure_reason
            orm.updated_at = invoice.updated_at

            session.commit()
            session.refresh(orm)
            return invoice_orm_to_domain(orm)
