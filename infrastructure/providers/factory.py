from domain.interfaces.invoice_provider import InvoiceProvider
from infrastructure.providers.registry import get_provider_class


def build_provider(country_code: str) -> InvoiceProvider:
    provider_cls = get_provider_class(country_code)
    return provider_cls()
