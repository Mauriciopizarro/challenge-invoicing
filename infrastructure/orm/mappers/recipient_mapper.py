from domain.models.fiscal_party import FiscalParty
from domain.models.recipient import Recipient
from domain.value_objects.recipient_id import RecipientId
from domain.value_objects.tax_id import TaxId
from infrastructure.orm.recipient_orm import RecipientORM


def recipient_domain_to_orm(recipient: Recipient) -> RecipientORM:
    return RecipientORM(
        id=recipient.id.value,
        country_code=recipient.country_code,
        legal_name=recipient.fiscal_party.legal_name,
        tax_id_type=recipient.fiscal_party.tax_id.id_type,
        tax_id_value=recipient.fiscal_party.tax_id.value,
        address=recipient.fiscal_party.address,
        extra=recipient.fiscal_party.extra,
        created_at=recipient.created_at,
        updated_at=recipient.updated_at,
    )


def recipient_orm_to_domain(orm: RecipientORM) -> Recipient:
    return Recipient(
        id=RecipientId(value=orm.id),
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
