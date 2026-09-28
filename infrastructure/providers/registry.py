from typing import Type

from domain.exceptions.unsupported_country import UnsupportedCountryError
from domain.interfaces.invoice_provider import InvoiceProvider

_REGISTRY: dict[str, Type[InvoiceProvider]] = {}


class ProviderAlreadyRegisteredError(Exception):
    # Deliberately not a domain exception: it fires at import time, before any
    # request exists, so it crashes the process instead of silently letting one
    # provider shadow another. Re-registering the SAME class is a no-op, not an
    # error, since that just means a module got reloaded.
    def __init__(self, country_code: str, existing: Type[InvoiceProvider], attempted: Type[InvoiceProvider]):
        self.country_code = country_code
        self.existing = existing
        self.attempted = attempted
        super().__init__(
            f"country_code '{country_code}' is already registered to "
            f"{existing.__module__}.{existing.__qualname__}; cannot also register "
            f"{attempted.__module__}.{attempted.__qualname__} for the same code"
        )


def register_provider(country_code: str):
    # The only integration point a new country needs to touch: subclass
    # InvoiceProvider, decorate it, drop the file in this package. No other
    # module (InvoiceService, controllers, Injector) needs to change.
    def decorator(provider_cls: Type[InvoiceProvider]) -> Type[InvoiceProvider]:
        code = country_code.upper()
        existing = _REGISTRY.get(code)
        if existing is not None and existing is not provider_cls:
            raise ProviderAlreadyRegisteredError(code, existing, provider_cls)
        _REGISTRY[code] = provider_cls
        return provider_cls

    return decorator


def get_provider_class(country_code: str) -> Type[InvoiceProvider]:
    try:
        return _REGISTRY[country_code.upper()]
    except KeyError:
        raise UnsupportedCountryError(country_code, supported=list(_REGISTRY.keys())) from None


def list_providers() -> dict[str, Type[InvoiceProvider]]:
    return dict(_REGISTRY)
