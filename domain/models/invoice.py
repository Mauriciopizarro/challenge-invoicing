from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from domain.models.fiscal_party import FiscalParty
from domain.value_objects.invoice_id import InvoiceId
from domain.value_objects.merchant_id import MerchantId
from domain.value_objects.recipient_id import RecipientId


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ISSUED = "issued"
    FAILED = "failed"


class Invoice(BaseModel):
    id: InvoiceId = Field(default_factory=lambda: InvoiceId(value=uuid4()))
    # Opaque reconciliation key in the merchant's own system (like Stripe's
    # internal customer.id), distinct from `recipient`'s legal fiscal identity.
    entity_id: str
    amount: Decimal
    currency: str
    country_code: str
    provider_used: str
    idempotency_key: str
    issuer_merchant_id: MerchantId
    # Snapshot of the merchant's fiscal_party at creation time, not a live
    # reference: an invoice must not change if the merchant edits its profile later.
    issuer: FiscalParty
    recipient_id: RecipientId
    recipient: FiscalParty
    status: InvoiceStatus = InvoiceStatus.PENDING
    external_reference: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    @staticmethod
    def create(
        entity_id: str,
        amount: Decimal,
        currency: str,
        country_code: str,
        provider_used: str,
        idempotency_key: str,
        issuer_merchant_id: MerchantId,
        issuer: FiscalParty,
        recipient_id: RecipientId,
        recipient: FiscalParty,
    ) -> "Invoice":
        if amount <= 0:
            raise ValueError("Invoice amount must be positive")

        return Invoice(
            entity_id=entity_id,
            amount=amount,
            currency=currency,
            country_code=country_code,
            provider_used=provider_used,
            idempotency_key=idempotency_key,
            issuer_merchant_id=issuer_merchant_id,
            issuer=issuer,
            recipient_id=recipient_id,
            recipient=recipient,
        )

    def start_processing(self) -> "Invoice":
        if self.status != InvoiceStatus.PENDING:
            raise ValueError(f"Cannot start processing an invoice in status '{self.status.value}'")
        return self.model_copy(update={"status": InvoiceStatus.PROCESSING, "updated_at": datetime.utcnow()})

    def mark_issued(self, external_reference: str) -> "Invoice":
        if self.status != InvoiceStatus.PROCESSING:
            raise ValueError(f"Cannot mark issued an invoice in status '{self.status.value}'")
        return self.model_copy(
            update={
                "status": InvoiceStatus.ISSUED,
                "external_reference": external_reference,
                "updated_at": datetime.utcnow(),
            }
        )

    def mark_failed(self, reason: str) -> "Invoice":
        if self.status != InvoiceStatus.PROCESSING:
            raise ValueError(f"Cannot mark failed an invoice in status '{self.status.value}'")
        return self.model_copy(
            update={
                "status": InvoiceStatus.FAILED,
                "failure_reason": reason,
                "updated_at": datetime.utcnow(),
            }
        )
