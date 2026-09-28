from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header, Response

from application.services.invoice_service import InvoiceService
from domain.value_objects.invoice_id import InvoiceId
from domain.value_objects.merchant_id import MerchantId
from domain.value_objects.recipient_id import RecipientId
from infrastructure.injector import Injector

from .dto.invoice_dto import InvoiceCreate, InvoiceCreatedResponse, InvoiceDetailResponse

router = APIRouter()


@router.post("", response_model=InvoiceCreatedResponse, status_code=202)
@inject
def create_invoice(
    data: InvoiceCreate,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1),
    service: InvoiceService = Depends(Provide[Injector.invoice_service]),
):
    result = service.create_invoice(
        entity_id=data.entity_id,
        amount=data.amount,
        issuer_merchant_id=MerchantId(value=data.issuer_merchant_id),
        recipient_id=RecipientId(value=data.recipient_id),
        idempotency_key=idempotency_key,
    )
    if not result.is_new:
        response.status_code = 200

    invoice = result.invoice
    return InvoiceCreatedResponse(
        invoice_id=str(invoice.id),
        status=invoice.status.value,
        provider_used=invoice.provider_used,
        external_reference=invoice.external_reference,
    )


@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
@inject
def get_invoice(
    invoice_id: UUID,
    service: InvoiceService = Depends(Provide[Injector.invoice_service]),
):
    invoice, attempts = service.get_invoice(InvoiceId(value=invoice_id))
    return InvoiceDetailResponse.from_domain(invoice, attempts)
