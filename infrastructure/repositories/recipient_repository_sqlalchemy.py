from typing import Optional

from domain.interfaces.recipient_repository import RecipientRepository
from domain.models.recipient import Recipient
from domain.value_objects.recipient_id import RecipientId
from infrastructure.db import SessionLocal
from infrastructure.orm.recipient_orm import RecipientORM
from infrastructure.orm.mappers.recipient_mapper import recipient_domain_to_orm, recipient_orm_to_domain


class SqlAlchemyRecipientRepository(RecipientRepository):

    def save(self, recipient: Recipient) -> Recipient:
        with SessionLocal() as session:
            orm = recipient_domain_to_orm(recipient)
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return recipient_orm_to_domain(orm)

    def update(self, recipient: Recipient) -> Recipient:
        with SessionLocal() as session:
            orm = session.get(RecipientORM, recipient.id.value)
            if orm is None:
                raise ValueError(f"Cannot update recipient '{recipient.id}': not found")

            orm.legal_name = recipient.fiscal_party.legal_name
            orm.tax_id_type = recipient.fiscal_party.tax_id.id_type
            orm.tax_id_value = recipient.fiscal_party.tax_id.value
            orm.address = recipient.fiscal_party.address
            orm.extra = recipient.fiscal_party.extra
            orm.updated_at = recipient.updated_at

            session.commit()
            session.refresh(orm)
            return recipient_orm_to_domain(orm)

    def get_by_id(self, recipient_id: RecipientId) -> Optional[Recipient]:
        with SessionLocal() as session:
            orm = session.get(RecipientORM, recipient_id.value)
            return recipient_orm_to_domain(orm) if orm else None
