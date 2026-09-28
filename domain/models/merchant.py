from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from domain.models.fiscal_party import FiscalParty
from domain.value_objects.merchant_id import MerchantId


class Merchant(BaseModel):
    """A tenant of the platform: one legal entity, in one tax jurisdiction,
    that issues invoices through this service.

    Invariant: one Merchant = one legal entity = one country_code. A company
    operating in multiple countries is modeled as multiple Merchant records
    (one per jurisdiction), each with its own tax id — not one Merchant with a
    variable country. This holds for AR/MX/BR; destination-based VAT schemes
    (e.g. EU OSS, where the issuer reports in the buyer's country) would break
    it, but none of the supported providers work that way.
    """

    id: MerchantId = Field(default_factory=lambda: MerchantId(value=uuid4()))
    country_code: str
    fiscal_party: FiscalParty
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    @staticmethod
    def create(country_code: str, fiscal_party: FiscalParty) -> "Merchant":
        return Merchant(country_code=country_code.upper(), fiscal_party=fiscal_party)

    def update_fiscal_party(self, fiscal_party: FiscalParty) -> "Merchant":
        # country_code is deliberately not changeable here: per the invariant
        # above, "this merchant is now a different jurisdiction" isn't a data
        # correction, it's a different legal entity — that means registering a
        # new Merchant, not editing this one.
        return self.model_copy(update={"fiscal_party": fiscal_party, "updated_at": datetime.utcnow()})
