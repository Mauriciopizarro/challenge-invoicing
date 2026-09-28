from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from domain.exceptions.idempotency_conflict import IdempotencyConflict
from domain.exceptions.invoice_not_found import InvoiceNotFoundError
from domain.exceptions.merchant_not_found import MerchantNotFoundError
from domain.exceptions.provider_errors import ProviderError
from domain.exceptions.recipient_not_found import RecipientNotFoundError
from domain.interfaces.invoice_attempt_repository import InvoiceAttemptRepository
from domain.interfaces.invoice_provider import InvoiceProvider, ProviderRequest
from domain.interfaces.invoice_repository import InvoiceRepository
from domain.interfaces.merchant_repository import MerchantRepository
from domain.interfaces.recipient_repository import RecipientRepository
from domain.models.invoice import Invoice
from domain.models.invoice_attempt import InvoiceAttempt
from domain.value_objects.invoice_id import InvoiceId
from domain.value_objects.merchant_id import MerchantId
from domain.value_objects.recipient_id import RecipientId
from application.services.provider_invoker import ProviderInvoker


@dataclass(frozen=True)
class CreateInvoiceResult:
    invoice: Invoice
    is_new: bool  # False when this call replayed an existing Idempotency-Key


class InvoiceService:
    def __init__(
        self,
        invoice_repo: InvoiceRepository,
        attempt_repo: InvoiceAttemptRepository,
        merchant_repo: MerchantRepository,
        recipient_repo: RecipientRepository,
        queue,
        provider_factory: Callable[[str], InvoiceProvider],
        provider_invoker: ProviderInvoker,
        job_timeout: int = 120,
    ):
        self.invoice_repo = invoice_repo
        self.attempt_repo = attempt_repo
        self.merchant_repo = merchant_repo
        self.recipient_repo = recipient_repo
        self.queue = queue
        self.provider_factory = provider_factory
        self.provider_invoker = provider_invoker
        self.job_timeout = job_timeout

    def create_invoice(
        self,
        entity_id: str,
        amount: Decimal,
        issuer_merchant_id: MerchantId,
        recipient_id: RecipientId,
        idempotency_key: str,
    ) -> CreateInvoiceResult:
        merchant = self.merchant_repo.get_by_id(issuer_merchant_id)
        if merchant is None:
            raise MerchantNotFoundError(issuer_merchant_id)

        recipient = self.recipient_repo.get_by_id(recipient_id)
        if recipient is None:
            raise RecipientNotFoundError(recipient_id)

        # Derived from the issuer, not chosen per invoice: you report to your
        # own jurisdiction's tax authority regardless of the customer's country.
        country_code = merchant.country_code

        provider = self.provider_factory(country_code)

        invoice = Invoice.create(
            entity_id=entity_id,
            amount=amount,
            # Derived, never client-supplied: a country has one valid currency.
            currency=provider.EXPECTED_CURRENCY,
            country_code=country_code,
            provider_used=provider.name,
            idempotency_key=idempotency_key,
            issuer_merchant_id=merchant.id,
            issuer=merchant.fiscal_party,
            recipient_id=recipient.id,
            recipient=recipient.fiscal_party,
        )

        try:
            saved = self.invoice_repo.save_new(invoice)
        except IdempotencyConflict:
            existing = self.invoice_repo.get_by_idempotency_key(idempotency_key)
            assert existing is not None
            return CreateInvoiceResult(invoice=existing, is_new=False)

        self.queue.enqueue(
            "infrastructure.queue.jobs.process_invoice_job",
            str(saved.id.value),
            job_timeout=self.job_timeout,
        )
        return CreateInvoiceResult(invoice=saved, is_new=True)

    def process_invoice(self, invoice_id: InvoiceId) -> None:
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if invoice is None:
            return

        if invoice.status.value != "pending":
            # Guards against a job being delivered more than once (e.g. a worker
            # restart re-queues an in-flight job): only a pending invoice gets
            # (re)processed, so we never call the provider twice for one invoice.
            return

        invoice = invoice.start_processing()
        invoice = self.invoice_repo.update(invoice)

        provider = self.provider_factory(invoice.country_code)
        request = ProviderRequest(
            entity_id=invoice.entity_id,
            amount=invoice.amount,
            currency=invoice.currency,
            country_code=invoice.country_code,
            issuer=invoice.issuer,
            recipient=invoice.recipient,
        )

        try:
            response = self.provider_invoker.invoke_with_retry(provider, request, invoice.id)
        except ProviderError as exc:
            invoice = invoice.mark_failed(str(exc))
            self.invoice_repo.update(invoice)
            return
        except Exception as exc:  # defensive: a provider bug must not crash the worker
            invoice = invoice.mark_failed(f"Unexpected error: {exc}")
            self.invoice_repo.update(invoice)
            return

        invoice = invoice.mark_issued(response.external_reference)
        self.invoice_repo.update(invoice)

    def get_invoice(self, invoice_id: InvoiceId) -> tuple[Invoice, list[InvoiceAttempt]]:
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if invoice is None:
            raise InvoiceNotFoundError(invoice_id)
        attempts = self.attempt_repo.list_by_invoice(invoice_id)
        return invoice, attempts
