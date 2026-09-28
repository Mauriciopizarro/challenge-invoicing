from domain.models.fiscal_party import FiscalParty
from domain.models.merchant import Merchant
from domain.value_objects.merchant_id import MerchantId
from domain.value_objects.tax_id import TaxId
from infrastructure.orm.merchant_orm import MerchantORM


def merchant_domain_to_orm(merchant: Merchant) -> MerchantORM:
    return MerchantORM(
        id=merchant.id.value,
        country_code=merchant.country_code,
        legal_name=merchant.fiscal_party.legal_name,
        tax_id_type=merchant.fiscal_party.tax_id.id_type,
        tax_id_value=merchant.fiscal_party.tax_id.value,
        address=merchant.fiscal_party.address,
        extra=merchant.fiscal_party.extra,
        created_at=merchant.created_at,
        updated_at=merchant.updated_at,
    )


def merchant_orm_to_domain(orm: MerchantORM) -> Merchant:
    return Merchant(
        id=MerchantId(value=orm.id),
        country_code=orm.country_code,
        fiscal_party=FiscalParty(
            legal_name=orm.legal_name,
            tax_id=TaxId(id_type=orm.tax_id_type, value=orm.tax_id_value),
            address=orm.address,
            extra=orm.extra,
        ),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
