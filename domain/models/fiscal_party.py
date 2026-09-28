from pydantic import BaseModel, Field

from domain.value_objects.tax_id import TaxId


class FiscalParty(BaseModel):
    legal_name: str = Field(min_length=1)
    tax_id: TaxId
    address: str = Field(min_length=1)
    # Well-known per-country fields that don't generalize across providers
    # (AR's condicion_iva, MX's regimen_fiscal/codigo_postal, BR's
    # inscricao_estadual); each adapter validates and reads the keys it needs.
    extra: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": True}
