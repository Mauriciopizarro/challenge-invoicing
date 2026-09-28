from uuid import UUID

from domain.value_objects.invoice_id import InvoiceId
from infrastructure.injector import container


def process_invoice_job(invoice_id: str) -> None:
    # Resolved by dotted path ("infrastructure.queue.jobs.process_invoice_job"),
    # not imported directly, to avoid a circular import: injector -> invoice_service
    # -> jobs -> injector.
    service = container.invoice_service()
    service.process_invoice(InvoiceId(value=UUID(invoice_id)))
