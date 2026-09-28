import time
from uuid import uuid4

from domain.exceptions.provider_errors import ProviderPermanentError, ProviderTransientError
from domain.interfaces.invoice_provider import InvoiceProvider, ProviderRequest, ProviderResponse
from infrastructure.providers.registry import register_provider


@register_provider("AR")
class ArgentinaInvoiceProvider(InvoiceProvider):

    name = "AFIP"
    timeout_seconds = 3.0
    max_retries = 3
    backoff_base = 0.5
    backoff_max = 8.0

    EXPECTED_CURRENCY = "ARS"
    EXPECTED_TAX_ID_TYPES = frozenset({"CUIT"})
    ISSUER_REQUIRED_EXTRA_FIELDS = ("condicion_iva",)
    RECIPIENT_REQUIRED_EXTRA_FIELDS = ("condicion_iva",)

    def __init__(self, fault_injector=None, simulated_latency_seconds: float = 0.05):
        self._fault_injector = fault_injector
        self._simulated_latency_seconds = simulated_latency_seconds

    def send_invoice(self, request: ProviderRequest) -> ProviderResponse:
        # currency is derived server-side; this only trips on data drift
        # between invoice creation and processing, not on client input.
        if request.currency != self.EXPECTED_CURRENCY:
            raise ProviderPermanentError(
                f"AR provider only accepts {self.EXPECTED_CURRENCY}, got '{request.currency}'"
            )

        self.validate_fiscal_data(request.issuer, request.recipient, regulator_name="AFIP")

        if self._fault_injector is not None:
            self._fault_injector()

        if self._simulated_latency_seconds > self.timeout_seconds:
            raise ProviderTransientError(f"AR provider timed out after {self.timeout_seconds}s")

        time.sleep(self._simulated_latency_seconds)

        cae = f"AR-{uuid4()}"
        return ProviderResponse(
            external_reference=cae,
            raw_payload={
                "cae": cae,
                "estado": "aprobado",
                "entidad": request.entity_id,
                "monto": str(request.amount),
                "emisor": {
                    "cuit": request.issuer.tax_id.value,
                    "razon_social": request.issuer.legal_name,
                    "condicion_iva": request.issuer.extra.get("condicion_iva"),
                },
                "receptor": {
                    "cuit": request.recipient.tax_id.value,
                    "razon_social": request.recipient.legal_name,
                    "condicion_iva": request.recipient.extra.get("condicion_iva"),
                },
            },
        )
