from uuid import UUID

from pydantic import BaseModel


class MerchantId(BaseModel):
    value: UUID

    model_config = {"frozen": True}

    def __str__(self) -> str:
        return str(self.value)
