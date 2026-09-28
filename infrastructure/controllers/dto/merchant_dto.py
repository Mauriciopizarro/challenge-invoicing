from datetime import datetime

from pydantic import BaseModel, Field

from domain.models.fiscal_party import FiscalParty
from domain.models.merchant import Merchant


class TaxIdDTO(BaseModel):
    id_type: str = Field(min_length=1, description="e.g. CUIT, RFC, CNPJ, CPF")
    value: str = Field(min_length=1)


class FiscalPartyDTO(BaseModel):
    legal_name: str = Field(min_length=1)
    tax_id: TaxIdDTO
    address: str = Field(min_length=1)
    extra: dict[str, str] = Field(
        default_factory=dict,
        description="Country-specific fiscal fields, e.g. condicion_iva (AR), regimen_fiscal/codigo_postal (MX), inscricao_estadual (BR)",
    )

    @staticmethod
    def from_domain(party: FiscalParty) -> "FiscalPartyDTO":
        return FiscalPartyDTO(
            legal_name=party.legal_name,
            tax_id=TaxIdDTO(id_type=party.tax_id.id_type, value=party.tax_id.value),
            address=party.address,
            extra=party.extra,
        )


class MerchantCreate(BaseModel):
    country_code: str = Field(pattern=r"^[A-Z]{2}$", description="ISO-3166 alpha-2 country code, e.g. AR, BR, MX")
    fiscal_party: FiscalPartyDTO


class MerchantResponse(BaseModel):
    merchant_id: str
    country_code: str
    fiscal_party: FiscalPartyDTO
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_domain(merchant: Merchant) -> "MerchantResponse":
        return MerchantResponse(
            merchant_id=str(merchant.id),
            country_code=merchant.country_code,
            fiscal_party=FiscalPartyDTO.from_domain(merchant.fiscal_party),
            created_at=merchant.created_at,
            updated_at=merchant.updated_at,
        )
