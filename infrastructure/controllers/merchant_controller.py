from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from application.services.merchant_service import MerchantService
from domain.value_objects.merchant_id import MerchantId
from infrastructure.injector import Injector

from .dto.merchant_dto import FiscalPartyDTO, MerchantCreate, MerchantResponse

router = APIRouter()


@router.post("", response_model=MerchantResponse, status_code=201)
@inject
def register_merchant(
    data: MerchantCreate,
    service: MerchantService = Depends(Provide[Injector.merchant_service]),
):
    merchant = service.register_merchant(
        country_code=data.country_code,
        legal_name=data.fiscal_party.legal_name,
        tax_id_type=data.fiscal_party.tax_id.id_type,
        tax_id_value=data.fiscal_party.tax_id.value,
        address=data.fiscal_party.address,
        extra=data.fiscal_party.extra,
    )
    return MerchantResponse.from_domain(merchant)


@router.get("/{merchant_id}", response_model=MerchantResponse)
@inject
def get_merchant(
    merchant_id: UUID,
    service: MerchantService = Depends(Provide[Injector.merchant_service]),
):
    merchant = service.get_merchant(MerchantId(value=merchant_id))
    return MerchantResponse.from_domain(merchant)


@router.put("/{merchant_id}", response_model=MerchantResponse)
@inject
def update_merchant(
    merchant_id: UUID,
    data: FiscalPartyDTO,
    service: MerchantService = Depends(Provide[Injector.merchant_service]),
):
    # No country_code here on purpose: this corrects data, it doesn't
    # re-jurisdiction the entity (see Merchant.update_fiscal_party).
    merchant = service.update_merchant(
        merchant_id=MerchantId(value=merchant_id),
        legal_name=data.legal_name,
        tax_id_type=data.tax_id.id_type,
        tax_id_value=data.tax_id.value,
        address=data.address,
        extra=data.extra,
    )
    return MerchantResponse.from_domain(merchant)
