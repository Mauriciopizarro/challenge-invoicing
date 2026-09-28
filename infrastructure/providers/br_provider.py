import time
from uuid import uuid4

from domain.exceptions.provider_errors import ProviderPermanentError, ProviderTransientError
from domain.interfaces.invoice_provider import InvoiceProvider, ProviderRequest, ProviderResponse
from infrastructure.providers.registry import register_provider


@register_provider("BR")
class BrazilInvoiceProvider(InvoiceProvider):

    name = "NFe"
    timeout_seconds = 5.0
    max_retries = 4
    backoff_base = 0.5
    backoff_max = 10.0

    EXPECTED_CURRENCY = "BRL"
    EXPECTED_TAX_ID_TYPES = frozenset({"CNPJ", "CPF"})
    ISSUER_REQUIRED_EXTRA_FIELDS = ("inscricao_estadual",)
    RECIPIENT_REQUIRED_EXTRA_FIELDS = ("inscricao_estadual",)

    def __init__(self, fault_injector=None, simulated_latency_seconds: float = 0.2):
        self._fault_injector = fault_injector
        self._simulated_latency_seconds = simulated_latency_seconds

    def send_invoice(self, request: ProviderRequest) -> ProviderResponse:
        # currency is derived server-side; this only trips on data drift
        # between invoice creation and processing, not on client input.
        if request.currency != self.EXPECTED_CURRENCY:
            raise ProviderPermanentError(
                f"BR provider only accepts {self.EXPECTED_CURRENCY}, got '{request.currency}'"
            )

        self.validate_fiscal_data(request.issuer, request.recipient, regulator_name="NF-e")

        if self._fault_injector is not None:
            self._fault_injector()

        if self._simulated_latency_seconds > self.timeout_seconds:
            raise ProviderTransientError(f"BR provider timed out after {self.timeout_seconds}s")

        time.sleep(self._simulated_latency_seconds)

        nfe_number = f"NFE-{uuid4()}"
        return ProviderResponse(
            external_reference=nfe_number,
            raw_payload={
                "nfe_number": nfe_number,
                "status": "autorizada",
                "entidade": request.entity_id,
                "valor": str(request.amount),
                "emitente": {
                    "cnpj_cpf": request.issuer.tax_id.value,
                    "razao_social": request.issuer.legal_name,
                    "inscricao_estadual": request.issuer.extra.get("inscricao_estadual"),
                },
                "destinatario": {
                    "cnpj_cpf": request.recipient.tax_id.value,
                    "razao_social": request.recipient.legal_name,
                    "inscricao_estadual": request.recipient.extra.get("inscricao_estadual"),
                },
            },
        )
