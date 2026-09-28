from abc import ABC, abstractmethod
from typing import Optional

from domain.models.merchant import Merchant
from domain.value_objects.merchant_id import MerchantId


class MerchantRepository(ABC):
    @abstractmethod
    def save(self, merchant: Merchant) -> Merchant:
        ...

    @abstractmethod
    def update(self, merchant: Merchant) -> Merchant:
        ...

    @abstractmethod
    def get_by_id(self, merchant_id: MerchantId) -> Optional[Merchant]:
        ...
