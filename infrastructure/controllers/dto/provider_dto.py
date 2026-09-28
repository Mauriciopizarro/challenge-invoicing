from pydantic import BaseModel


class ProviderInfoResponse(BaseModel):
    country_code: str
    provider: str
