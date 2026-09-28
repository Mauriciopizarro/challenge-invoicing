from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from domain.models.invoice import Invoice
from domain.models.invoice_attempt import InvoiceAttempt

from .merchant_dto import FiscalPartyDTO


class InvoiceCreate(BaseModel):
    entity_id: str = Field(
        min_length=1,
        description="Opaque internal customer id in the merchant's own system (reconciliation key, not fiscal identity)",
    )
    amount: Decimal = Field(gt=0)
    issuer_merchant_id: UUID = Field(
        description="Id of a Merchant registered via POST /merchants — country_code, issuer, and currency are all derived from it",
    )
    recipient_id: UUID = Field(
        description="Id of a Recipient registered via POST /recipients (always required — this is a B2B platform, there is no anonymous 'consumidor final' case)",
    )


class InvoiceCreatedResponse(BaseModel):
    invoice_id: str
    status: str
    provider_used: str
    external_reference: Optional[str]


class InvoiceAttemptResponse(BaseModel):
    attempt_number: int
    provider: str
    request_payload: dict[str, Any]
    response_payload: Optional[dict[str, Any]]
    error_message: Optional[str]
    status: str
    duration_ms: int
    started_at: datetime
    finished_at: datetime

    @staticmethod
    def from_domain(attempt: InvoiceAttempt) -> "InvoiceAttemptResponse":
        return InvoiceAttemptResponse(
            attempt_number=attempt.attempt_number,
            provider=attempt.provider,
            request_payload=attempt.request_payload,
            response_payload=attempt.response_payload,
            error_message=attempt.error_message,
            status=attempt.status.value,
            duration_ms=attempt.duration_ms,
            started_at=attempt.started_at,
            finished_at=attempt.finished_at,
        )


class InvoiceDetailResponse(BaseModel):
    invoice_id: str
    entity_id: str
    amount: Decimal
    currency: str
    country_code: str
    provider_used: str
    status: str
    external_reference: Optional[str]
    failure_reason: Optional[str]
    issuer_merchant_id: str
    issuer: FiscalPartyDTO
    recipient_id: str
    recipient: FiscalPartyDTO
    created_at: datetime
    updated_at: datetime
    attempts: list[InvoiceAttemptResponse]

    @staticmethod
    def from_domain(invoice: Invoice, attempts: list[InvoiceAttempt]) -> "InvoiceDetailResponse":
        return InvoiceDetailResponse(
            invoice_id=str(invoice.id),
            entity_id=invoice.entity_id,
            amount=invoice.amount,
            currency=invoice.currency,
            country_code=invoice.country_code,
            provider_used=invoice.provider_used,
            status=invoice.status.value,
            external_reference=invoice.external_reference,
            failure_reason=invoice.failure_reason,
            issuer_merchant_id=str(invoice.issuer_merchant_id),
            issuer=FiscalPartyDTO.from_domain(invoice.issuer),
            recipient_id=str(invoice.recipient_id),
            recipient=FiscalPartyDTO.from_domain(invoice.recipient),
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
            attempts=[InvoiceAttemptResponse.from_domain(a) for a in attempts],
        )
