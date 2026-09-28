from domain.models.fiscal_party import FiscalParty
from domain.models.invoice import Invoice, InvoiceStatus
from domain.value_objects.invoice_id import InvoiceId
from domain.value_objects.merchant_id import MerchantId
from domain.value_objects.recipient_id import RecipientId
from infrastructure.orm.invoice_orm import InvoiceORM


def invoice_domain_to_orm(invoice: Invoice) -> InvoiceORM:
    return InvoiceORM(
        id=invoice.id.value,
        entity_id=invoice.entity_id,
        amount=invoice.amount,
        currency=invoice.currency,
        country_code=invoice.country_code,
        provider_used=invoice.provider_used,
        status=invoice.status.value,
        external_reference=invoice.external_reference,
        failure_reason=invoice.failure_reason,
        idempotency_key=invoice.idempotency_key,
        issuer_merchant_id=invoice.issuer_merchant_id.value,
        recipient_id=invoice.recipient_id.value,
        issuer=invoice.issuer.model_dump(mode="json"),
        recipient=invoice.recipient.model_dump(mode="json"),
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


def invoice_orm_to_domain(orm: InvoiceORM) -> Invoice:
    return Invoice(
        id=InvoiceId(value=orm.id),
        entity_id=orm.entity_id,
        amount=orm.amount,
        currency=orm.currency,
        country_code=orm.country_code,
        provider_used=orm.provider_used,
        status=InvoiceStatus(orm.status),
        external_reference=orm.external_reference,
        failure_reason=orm.failure_reason,
        idempotency_key=orm.idempotency_key,
        issuer_merchant_id=MerchantId(value=orm.issuer_merchant_id),
        recipient_id=RecipientId(value=orm.recipient_id),
        issuer=FiscalParty(**orm.issuer),
        recipient=FiscalParty(**orm.recipient),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
