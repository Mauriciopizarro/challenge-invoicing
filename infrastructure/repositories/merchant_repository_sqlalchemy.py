from typing import Optional

from domain.interfaces.merchant_repository import MerchantRepository
from domain.models.merchant import Merchant
from domain.value_objects.merchant_id import MerchantId
from infrastructure.db import SessionLocal
from infrastructure.orm.merchant_orm import MerchantORM
from infrastructure.orm.mappers.merchant_mapper import merchant_domain_to_orm, merchant_orm_to_domain


class SqlAlchemyMerchantRepository(MerchantRepository):

    def save(self, merchant: Merchant) -> Merchant:
        with SessionLocal() as session:
            orm = merchant_domain_to_orm(merchant)
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return merchant_orm_to_domain(orm)

    def update(self, merchant: Merchant) -> Merchant:
        with SessionLocal() as session:
            orm = session.get(MerchantORM, merchant.id.value)
            if orm is None:
                raise ValueError(f"Cannot update merchant '{merchant.id}': not found")

            orm.legal_name = merchant.fiscal_party.legal_name
            orm.tax_id_type = merchant.fiscal_party.tax_id.id_type
            orm.tax_id_value = merchant.fiscal_party.tax_id.value
            orm.address = merchant.fiscal_party.address
            orm.extra = merchant.fiscal_party.extra
            orm.updated_at = merchant.updated_at

            session.commit()
            session.refresh(orm)
            return merchant_orm_to_domain(orm)

    def get_by_id(self, merchant_id: MerchantId) -> Optional[Merchant]:
        with SessionLocal() as session:
            orm = session.get(MerchantORM, merchant_id.value)
            return merchant_orm_to_domain(orm) if orm else None
