from fastapi import APIRouter

from infrastructure.providers.registry import list_providers

from .dto.provider_dto import ProviderInfoResponse

router = APIRouter()


@router.get("", response_model=list[ProviderInfoResponse])
def list_supported_providers():
    return [
        ProviderInfoResponse(country_code=country_code, provider=provider_cls.name)
        for country_code, provider_cls in sorted(list_providers().items())
    ]
