from abc import ABC, abstractmethod
from typing import Optional

from domain.models.recipient import Recipient
from domain.value_objects.recipient_id import RecipientId


class RecipientRepository(ABC):
    @abstractmethod
    def save(self, recipient: Recipient) -> Recipient:
        ...

    @abstractmethod
    def update(self, recipient: Recipient) -> Recipient:
        ...

    @abstractmethod
    def get_by_id(self, recipient_id: RecipientId) -> Optional[Recipient]:
        ...
