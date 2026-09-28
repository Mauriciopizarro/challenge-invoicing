import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.orm.base import Base


class InvoiceAttemptORM(Base):
    __tablename__ = "invoice_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    provider = Column(String(50), nullable=False)
    request_payload = Column(JSONB, nullable=False)
    response_payload = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    status = Column(String(20), nullable=False)
    duration_ms = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("invoice_id", "attempt_number", name="uq_attempt_per_invoice"),)
