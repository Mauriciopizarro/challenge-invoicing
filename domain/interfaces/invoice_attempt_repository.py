from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from domain.models.invoice_attempt import AttemptStatus, InvoiceAttempt
from domain.value_objects.invoice_id import InvoiceId


class InvoiceAttemptRepository(ABC):
    @abstractmethod
    def record(
        self,
        invoice_id: InvoiceId,
        attempt_number: int,
        provider: str,
        request_payload: dict[str, Any],
        response_payload: Optional[dict[str, Any]],
        error_message: Optional[str],
        status: AttemptStatus,
        duration_ms: int,
        started_at: datetime,
        finished_at: datetime,
    ) -> InvoiceAttempt:
        ...

    @abstractmethod
    def list_by_invoice(self, invoice_id: InvoiceId) -> list[InvoiceAttempt]:
        ...
