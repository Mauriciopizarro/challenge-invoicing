from pydantic import BaseModel, Field


class TaxId(BaseModel):
    """A country's tax identifier (CUIT, RFC, CNPJ, CPF, ...).

    `id_type` is a free string, not a closed Enum: which types are valid for a
    given country is a per-provider concern (see InvoiceProvider.EXPECTED_TAX_ID_TYPES),
    the same way currency validation works today. A closed Enum here would force
    editing shared domain code every time a new country is added, breaking the
    "add a country without touching the core" property the registry already gives.
    """

    id_type: str = Field(min_length=1)
    value: str = Field(min_length=1)

    model_config = {"frozen": True}
