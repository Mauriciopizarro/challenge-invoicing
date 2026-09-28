from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from domain.value_objects.invoice_id import InvoiceId


class AttemptStatus(str, Enum):
    SUCCESS = "success"
    FAILED_TRANSIENT = "failed_transient"
    FAILED_PERMANENT = "failed_permanent"


class InvoiceAttempt(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    invoice_id: InvoiceId
    attempt_number: int
    provider: str
    request_payload: dict[str, Any]
    response_payload: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    status: AttemptStatus
    duration_ms: int
    started_at: datetime
    finished_at: datetime

    model_config = {"frozen": True, "arbitrary_types_allowed": True}
