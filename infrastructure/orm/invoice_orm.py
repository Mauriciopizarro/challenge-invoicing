import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.orm.base import Base


class InvoiceORM(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    country_code = Column(String(2), nullable=False)
    provider_used = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    external_reference = Column(String(100), nullable=True)
    failure_reason = Column(Text, nullable=True)
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    issuer_merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("recipients.id"), nullable=False, index=True)
    # Point-in-time snapshots, not live references to merchants/recipients:
    # an invoice must not change if a profile is edited later. The FKs above
    # exist only for traceability, never as the source of truth here.
    issuer = Column(JSONB, nullable=False)
    recipient = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
