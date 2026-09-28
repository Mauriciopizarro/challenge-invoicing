from datetime import datetime

from pydantic import BaseModel, Field

from domain.models.recipient import Recipient

from .merchant_dto import FiscalPartyDTO


class RecipientCreate(BaseModel):
    country_code: str = Field(pattern=r"^[A-Z]{2}$", description="ISO-3166 alpha-2 country code, e.g. AR, BR, MX")
    fiscal_party: FiscalPartyDTO


class RecipientResponse(BaseModel):
    recipient_id: str
    country_code: str
    fiscal_party: FiscalPartyDTO
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_domain(recipient: Recipient) -> "RecipientResponse":
        return RecipientResponse(
            recipient_id=str(recipient.id),
            country_code=recipient.country_code,
            fiscal_party=FiscalPartyDTO.from_domain(recipient.fiscal_party),
            created_at=recipient.created_at,
            updated_at=recipient.updated_at,
        )
