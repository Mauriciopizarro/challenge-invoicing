from uuid import UUID

from pydantic import BaseModel


class RecipientId(BaseModel):
    value: UUID

    model_config = {"frozen": True}

    def __str__(self) -> str:
        return str(self.value)
