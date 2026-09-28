from typing import Callable

from domain.exceptions.invalid_fiscal_data import InvalidFiscalDataError
from domain.exceptions.recipient_not_found import RecipientNotFoundError
from domain.interfaces.invoice_provider import InvoiceProvider
from domain.interfaces.recipient_repository import RecipientRepository
from domain.models.fiscal_party import FiscalParty
from domain.models.recipient import Recipient
from domain.value_objects.recipient_id import RecipientId
from domain.value_objects.tax_id import TaxId


class RecipientService:
    def __init__(
        self,
        recipient_repo: RecipientRepository,
        provider_factory: Callable[[str], InvoiceProvider],
    ):
        self.recipient_repo = recipient_repo
        self.provider_factory = provider_factory

    def _build_valid_fiscal_party(
        self,
        provider: InvoiceProvider,
        country_code: str,
        legal_name: str,
        tax_id_type: str,
        tax_id_value: str,
        address: str,
        extra: dict[str, str],
    ) -> FiscalParty:
        fiscal_party = FiscalParty(
            legal_name=legal_name,
            tax_id=TaxId(id_type=tax_id_type, value=tax_id_value),
            address=address,
            extra=extra or {},
        )

        # Mirrors MerchantService's fail-fast check, against
        # RECIPIENT_REQUIRED_EXTRA_FIELDS instead of ISSUER_* (e.g. MX's
        # codigo_postal is required only for the recipient).
        problem = provider.fiscal_data_problem(
            fiscal_party, role="recipient", required=provider.RECIPIENT_REQUIRED_EXTRA_FIELDS,
            regulator_name=provider.name,
        )
        if problem:
            raise InvalidFiscalDataError(country_code, problem)

        return fiscal_party

    def register_recipient(
        self,
        country_code: str,
        legal_name: str,
        tax_id_type: str,
        tax_id_value: str,
        address: str,
        extra: dict[str, str],
    ) -> Recipient:
        provider = self.provider_factory(country_code)
        fiscal_party = self._build_valid_fiscal_party(
            provider, country_code, legal_name, tax_id_type, tax_id_value, address, extra
        )
        recipient = Recipient.create(country_code, fiscal_party)
        return self.recipient_repo.save(recipient)

    def update_recipient(
        self,
        recipient_id: RecipientId,
        legal_name: str,
        tax_id_type: str,
        tax_id_value: str,
        address: str,
        extra: dict[str, str],
    ) -> Recipient:
        recipient = self.recipient_repo.get_by_id(recipient_id)
        if recipient is None:
            raise RecipientNotFoundError(recipient_id)

        provider = self.provider_factory(recipient.country_code)
        fiscal_party = self._build_valid_fiscal_party(
            provider, recipient.country_code, legal_name, tax_id_type, tax_id_value, address, extra
        )

        updated = recipient.update_fiscal_party(fiscal_party)
        return self.recipient_repo.update(updated)

    def get_recipient(self, recipient_id: RecipientId) -> Recipient:
        recipient = self.recipient_repo.get_by_id(recipient_id)
        if recipient is None:
            raise RecipientNotFoundError(recipient_id)
        return recipient
