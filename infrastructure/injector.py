from dependency_injector import containers, providers
from rq import Queue

from application.services.invoice_service import InvoiceService
from application.services.merchant_service import MerchantService
from application.services.provider_invoker import ProviderInvoker
from application.services.recipient_service import RecipientService
from config import settings
from infrastructure.providers.factory import build_provider
from infrastructure.queue.redis_conn import build_redis_connection
from infrastructure.repositories.invoice_attempt_repository_sqlalchemy import SqlAlchemyInvoiceAttemptRepository
from infrastructure.repositories.invoice_repository_sqlalchemy import SqlAlchemyInvoiceRepository
from infrastructure.repositories.merchant_repository_sqlalchemy import SqlAlchemyMerchantRepository
from infrastructure.repositories.recipient_repository_sqlalchemy import SqlAlchemyRecipientRepository


class Injector(containers.DeclarativeContainer):
    redis_conn = providers.Singleton(build_redis_connection)
    invoice_queue = providers.Singleton(Queue, name="invoices", connection=redis_conn)

    invoice_repo = providers.Singleton(SqlAlchemyInvoiceRepository)
    attempt_repo = providers.Singleton(SqlAlchemyInvoiceAttemptRepository)
    merchant_repo = providers.Singleton(SqlAlchemyMerchantRepository)
    recipient_repo = providers.Singleton(SqlAlchemyRecipientRepository)

    provider_invoker = providers.Factory(ProviderInvoker, attempt_repo=attempt_repo)

    merchant_service = providers.Factory(
        MerchantService,
        merchant_repo=merchant_repo,
        provider_factory=providers.Object(build_provider),
    )

    recipient_service = providers.Factory(
        RecipientService,
        recipient_repo=recipient_repo,
        provider_factory=providers.Object(build_provider),
    )

    invoice_service = providers.Factory(
        InvoiceService,
        invoice_repo=invoice_repo,
        attempt_repo=attempt_repo,
        merchant_repo=merchant_repo,
        recipient_repo=recipient_repo,
        queue=invoice_queue,
        provider_factory=providers.Object(build_provider),
        provider_invoker=provider_invoker,
        job_timeout=settings.RQ_JOB_TIMEOUT,
    )

container = Injector()
