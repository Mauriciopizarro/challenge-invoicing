from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from domain.exceptions.provider_errors import ProviderPermanentError
from domain.models.fiscal_party import FiscalParty


@dataclass(frozen=True)
class ProviderRequest:
    entity_id: str
    amount: Decimal
    currency: str
    country_code: str
    issuer: FiscalParty
    recipient: FiscalParty


@dataclass(frozen=True)
class ProviderResponse:
    external_reference: str
    raw_payload: dict[str, Any]


class InvoiceProvider(ABC):

    name: str
    timeout_seconds: float = 3.0
    max_retries: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 8.0

    # ISO-4217 currency this provider's country issues invoices in (AR: "ARS").
    # Derived server-side, never client-supplied: a country has one valid currency.
    EXPECTED_CURRENCY: str

    EXPECTED_TAX_ID_TYPES: frozenset[str] = frozenset()
    # Issuer and recipient requirements can differ (e.g. MX's codigo_postal is
    # only required for the recipient, per CFDI 4.0's "Domicilio Fiscal Receptor").
    ISSUER_REQUIRED_EXTRA_FIELDS: tuple[str, ...] = ()
    RECIPIENT_REQUIRED_EXTRA_FIELDS: tuple[str, ...] = ()

    @abstractmethod
    def send_invoice(self, request: ProviderRequest) -> ProviderResponse:
        ...

    def missing_fiscal_fields(self, party: FiscalParty, required: tuple[str, ...]) -> list[str]:
        return [field for field in required if not party.extra.get(field)]

    def fiscal_data_problem(self, party: FiscalParty, role: str, required: tuple[str, ...], regulator_name: str) -> str | None:
        # Shared by validate_fiscal_data (invoice processing) and MerchantService/
        # RecipientService (registration/update), so registration and invoicing
        # can never disagree about what "valid" means for a country.
        if self.EXPECTED_TAX_ID_TYPES and party.tax_id.id_type not in self.EXPECTED_TAX_ID_TYPES:
            expected = "/".join(sorted(self.EXPECTED_TAX_ID_TYPES))
            return (
                f"{regulator_name} requires the {role}'s tax id type to be {expected}, "
                f"got '{party.tax_id.id_type}'"
            )

        missing = self.missing_fiscal_fields(party, required)
        if missing:
            return (
                f"{regulator_name} requires the {role}'s fiscal field(s) {', '.join(missing)}, "
                "which are missing"
            )

        return None

    def validate_fiscal_data(self, issuer: FiscalParty, recipient: FiscalParty, regulator_name: str) -> None:
        # Revalidates the issuer too, even though Merchant registration already
        # checked it: defense in depth against a merchant ending up with
        # incomplete data later (e.g. required fields changing for a country
        # after older merchants were already registered).
        for role, party, required in (
            ("issuer", issuer, self.ISSUER_REQUIRED_EXTRA_FIELDS),
            ("recipient", recipient, self.RECIPIENT_REQUIRED_EXTRA_FIELDS),
        ):
            problem = self.fiscal_data_problem(party, role, required, regulator_name)
            if problem:
                raise ProviderPermanentError(problem)
