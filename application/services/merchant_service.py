from typing import Callable

from domain.exceptions.invalid_fiscal_data import InvalidFiscalDataError
from domain.exceptions.merchant_not_found import MerchantNotFoundError
from domain.interfaces.invoice_provider import InvoiceProvider
from domain.interfaces.merchant_repository import MerchantRepository
from domain.models.fiscal_party import FiscalParty
from domain.models.merchant import Merchant
from domain.value_objects.merchant_id import MerchantId
from domain.value_objects.tax_id import TaxId


class MerchantService:
    def __init__(
        self,
        merchant_repo: MerchantRepository,
        provider_factory: Callable[[str], InvoiceProvider],
    ):
        self.merchant_repo = merchant_repo
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

        # Same check the provider runs on the issuer at invoice time, so bad
        # data gets rejected here (422, fail-fast) instead of only surfacing
        # later as a failed invoice.
        problem = provider.fiscal_data_problem(
            fiscal_party, role="issuer", required=provider.ISSUER_REQUIRED_EXTRA_FIELDS, regulator_name=provider.name
        )
        if problem:
            raise InvalidFiscalDataError(country_code, problem)

        return fiscal_party

    def register_merchant(
        self,
        country_code: str,
        legal_name: str,
        tax_id_type: str,
        tax_id_value: str,
        address: str,
        extra: dict[str, str],
    ) -> Merchant:
        # Resolving the provider first fails fast (422 unsupported_country)
        # before touching the database, same pattern as InvoiceService.create_invoice.
        provider = self.provider_factory(country_code)
        fiscal_party = self._build_valid_fiscal_party(
            provider, country_code, legal_name, tax_id_type, tax_id_value, address, extra
        )
        merchant = Merchant.create(country_code, fiscal_party)
        return self.merchant_repo.save(merchant)

    def update_merchant(
        self,
        merchant_id: MerchantId,
        legal_name: str,
        tax_id_type: str,
        tax_id_value: str,
        address: str,
        extra: dict[str, str],
    ) -> Merchant:
        merchant = self.merchant_repo.get_by_id(merchant_id)
        if merchant is None:
            raise MerchantNotFoundError(merchant_id)

        # country_code is not an input here — see Merchant.update_fiscal_party.
        provider = self.provider_factory(merchant.country_code)
        fiscal_party = self._build_valid_fiscal_party(
            provider, merchant.country_code, legal_name, tax_id_type, tax_id_value, address, extra
        )

        updated = merchant.update_fiscal_party(fiscal_party)
        return self.merchant_repo.update(updated)

    def get_merchant(self, merchant_id: MerchantId) -> Merchant:
        merchant = self.merchant_repo.get_by_id(merchant_id)
        if merchant is None:
            raise MerchantNotFoundError(merchant_id)
        return merchant
