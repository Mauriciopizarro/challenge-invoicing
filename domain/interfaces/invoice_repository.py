from abc import ABC, abstractmethod
from typing import Optional

from domain.models.invoice import Invoice
from domain.value_objects.invoice_id import InvoiceId


class InvoiceRepository(ABC):
    @abstractmethod
    def save_new(self, invoice: Invoice) -> Invoice:
        ...

    @abstractmethod
    def get_by_id(self, invoice_id: InvoiceId) -> Optional[Invoice]:
        ...

    @abstractmethod
    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Invoice]:
        ...

    @abstractmethod
    def update(self, invoice: Invoice) -> Invoice:
        ...
