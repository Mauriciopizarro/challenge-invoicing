import pytest

from domain.interfaces.invoice_provider import InvoiceProvider, ProviderRequest, ProviderResponse
from infrastructure.providers.registry import (
    ProviderAlreadyRegisteredError,
    _REGISTRY,
    get_provider_class,
    list_providers,
    register_provider,
)


class _DummyProvider(InvoiceProvider):
    name = "DUMMY"

    def send_invoice(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _isolate_registry():
    # AR/BR are auto-discovered at process startup by infrastructure.providers'
    # __init__.py; snapshot/restore around each test so these throwaway
    # registrations never leak into other tests (or into list_providers()
    # used by the real /providers endpoint tests).
    snapshot = dict(_REGISTRY)
    yield
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)


def test_registering_a_new_country_code_works():
    @register_provider("ZZ")
    class ZetaProvider(_DummyProvider):
        name = "ZETA"

    assert get_provider_class("zz") is ZetaProvider  # lookup is case-insensitive
    assert "ZZ" in list_providers()


def test_registering_a_different_class_for_an_already_registered_code_raises():
    @register_provider("ZZ")
    class FirstZetaProvider(_DummyProvider):
        name = "ZETA-1"

    with pytest.raises(ProviderAlreadyRegisteredError) as exc_info:

        @register_provider("ZZ")
        class SecondZetaProvider(_DummyProvider):
            name = "ZETA-2"

    assert "ZZ" in str(exc_info.value)
    # The first registration must survive untouched — no silent overwrite.
    assert get_provider_class("ZZ") is FirstZetaProvider


def test_registering_the_same_class_twice_is_a_no_op():
    @register_provider("ZZ")
    class ZetaProvider(_DummyProvider):
        name = "ZETA"

    # Re-applying the decorator to the SAME class object (e.g. a module
    # reloaded twice) must not raise.
    register_provider("ZZ")(ZetaProvider)

    assert get_provider_class("ZZ") is ZetaProvider
