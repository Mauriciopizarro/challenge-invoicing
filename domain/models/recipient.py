from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from domain.models.fiscal_party import FiscalParty
from domain.value_objects.recipient_id import RecipientId


class Recipient(BaseModel):
    # Global directory, not owned by a specific Merchant: without real
    # authentication, a "belongs to this merchant" boundary would enforce
    # nothing, so it isn't modeled here (see README).
    id: RecipientId = Field(default_factory=lambda: RecipientId(value=uuid4()))
    # country_code only picks which provider's rules validate this recipient
    # at registration/update time (mirrors Merchant); it does NOT restrict
    # which invoices' country this recipient can be used for. That check
    # happens per-invoice, in InvoiceProvider.validate_fiscal_data.
    country_code: str
    fiscal_party: FiscalParty
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    @staticmethod
    def create(country_code: str, fiscal_party: FiscalParty) -> "Recipient":
        return Recipient(country_code=country_code.upper(), fiscal_party=fiscal_party)

    def update_fiscal_party(self, fiscal_party: FiscalParty) -> "Recipient":
        return self.model_copy(update={"fiscal_party": fiscal_party, "updated_at": datetime.utcnow()})
