"""Single source of truth for valid fiscal data per country, reused by unit
tests (domain objects) and integration tests (JSON payloads).
"""
from domain.models.fiscal_party import FiscalParty
from domain.value_objects.tax_id import TaxId

_DEFAULTS = {
    "AR": {
        "legal_name": "Acme Argentina SA",
        "tax_id": {"id_type": "CUIT", "value": "30-12345678-9"},
        "address": "Av. Corrientes 1234, CABA",
        "extra": {"condicion_iva": "Responsable Inscripto"},
    },
    "BR": {
        "legal_name": "Acme Brasil LTDA",
        "tax_id": {"id_type": "CNPJ", "value": "12.345.678/0001-99"},
        "address": "Av. Paulista 1000, Sao Paulo",
        "extra": {"inscricao_estadual": "ISENTO"},
    },
    "MX": {
        "legal_name": "Acme Mexico SA de CV",
        "tax_id": {"id_type": "RFC", "value": "ACM010101AAA"},
        "address": "Reforma 222, CDMX",
        "extra": {"regimen_fiscal": "601", "codigo_postal": "06600"},
    },
}


def fiscal_party_payload(country_code: str, **overrides) -> dict:
    data = dict(_DEFAULTS[country_code])
    data["tax_id"] = dict(data["tax_id"])
    data["extra"] = dict(data["extra"])
    data.update(overrides)
    return data


def fiscal_party(country_code: str, **overrides) -> FiscalParty:
    data = fiscal_party_payload(country_code, **overrides)
    tax_id_data = data["tax_id"]
    tax_id = tax_id_data if isinstance(tax_id_data, TaxId) else TaxId(**tax_id_data)
    return FiscalParty(legal_name=data["legal_name"], tax_id=tax_id, address=data["address"], extra=data["extra"])
