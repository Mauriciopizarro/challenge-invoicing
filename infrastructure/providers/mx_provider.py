import time
from uuid import uuid4

from domain.exceptions.provider_errors import ProviderPermanentError, ProviderTransientError
from domain.interfaces.invoice_provider import InvoiceProvider, ProviderRequest, ProviderResponse
from infrastructure.providers.registry import register_provider


@register_provider("MX")
class MexicoInvoiceProvider(InvoiceProvider):

    name = "SAT"
    timeout_seconds = 3.0
    max_retries = 2
    backoff_base = 0.5
    backoff_max = 10.0

    EXPECTED_CURRENCY = "MXN"
    EXPECTED_TAX_ID_TYPES = frozenset({"RFC"})
    ISSUER_REQUIRED_EXTRA_FIELDS = ("regimen_fiscal",)
    RECIPIENT_REQUIRED_EXTRA_FIELDS = ("regimen_fiscal", "codigo_postal")

    def __init__(self, fault_injector=None, simulated_latency_seconds: float = 0.2):
        self._fault_injector = fault_injector
        self._simulated_latency_seconds = simulated_latency_seconds

    def send_invoice(self, request: ProviderRequest) -> ProviderResponse:
        # currency is derived server-side; this only trips on data drift
        # between invoice creation and processing, not on client input.
        if request.currency != self.EXPECTED_CURRENCY:
            raise ProviderPermanentError(
                f"MX provider only accepts {self.EXPECTED_CURRENCY}, got '{request.currency}'"
            )

        self.validate_fiscal_data(request.issuer, request.recipient, regulator_name="SAT")

        if self._fault_injector is not None:
            self._fault_injector()

        if self._simulated_latency_seconds > self.timeout_seconds:
            raise ProviderTransientError(f"MX provider timed out after {self.timeout_seconds}s")

        time.sleep(self._simulated_latency_seconds)

        cfdi_number = f"CFDI-{uuid4()}"
        return ProviderResponse(
            external_reference=cfdi_number,
            raw_payload={
                "cfdi_number": cfdi_number,
                "status": "autorizada",
                "entidad": request.entity_id,
                "valor": str(request.amount),
                "emisor": {
                    "rfc": request.issuer.tax_id.value,
                    "razon_social": request.issuer.legal_name,
                    "regimen_fiscal": request.issuer.extra.get("regimen_fiscal"),
                },
                "receptor": {
                    "rfc": request.recipient.tax_id.value,
                    "razon_social": request.recipient.legal_name,
                    "regimen_fiscal": request.recipient.extra.get("regimen_fiscal"),
                    "codigo_postal": request.recipient.extra.get("codigo_postal"),
                },
            },
        )
