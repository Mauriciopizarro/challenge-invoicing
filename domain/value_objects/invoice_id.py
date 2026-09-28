from uuid import UUID

from pydantic import BaseModel


class InvoiceId(BaseModel):
    value: UUID

    model_config = {"frozen": True}

    def __str__(self) -> str:
        return str(self.value)
