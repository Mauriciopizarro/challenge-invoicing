from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from application.services.recipient_service import RecipientService
from domain.value_objects.recipient_id import RecipientId
from infrastructure.injector import Injector

from .dto.merchant_dto import FiscalPartyDTO
from .dto.recipient_dto import RecipientCreate, RecipientResponse

router = APIRouter()


@router.post("", response_model=RecipientResponse, status_code=201)
@inject
def register_recipient(
    data: RecipientCreate,
    service: RecipientService = Depends(Provide[Injector.recipient_service]),
):
    recipient = service.register_recipient(
        country_code=data.country_code,
        legal_name=data.fiscal_party.legal_name,
        tax_id_type=data.fiscal_party.tax_id.id_type,
        tax_id_value=data.fiscal_party.tax_id.value,
        address=data.fiscal_party.address,
        extra=data.fiscal_party.extra,
    )
    return RecipientResponse.from_domain(recipient)


@router.get("/{recipient_id}", response_model=RecipientResponse)
@inject
def get_recipient(
    recipient_id: UUID,
    service: RecipientService = Depends(Provide[Injector.recipient_service]),
):
    recipient = service.get_recipient(RecipientId(value=recipient_id))
    return RecipientResponse.from_domain(recipient)


@router.put("/{recipient_id}", response_model=RecipientResponse)
@inject
def update_recipient(
    recipient_id: UUID,
    data: FiscalPartyDTO,
    service: RecipientService = Depends(Provide[Injector.recipient_service]),
):
    # No country_code here on purpose: same reasoning as
    # Merchant.update_fiscal_party.
    recipient = service.update_recipient(
        recipient_id=RecipientId(value=recipient_id),
        legal_name=data.legal_name,
        tax_id_type=data.tax_id.id_type,
        tax_id_value=data.tax_id.value,
        address=data.address,
        extra=data.extra,
    )
    return RecipientResponse.from_domain(recipient)
