import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/invoicing")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import fakeredis
import pytest
from dependency_injector import providers as di_providers
from rq import Queue
from sqlalchemy import text
from starlette.testclient import TestClient

import main
from application.services.invoice_service import InvoiceService
from infrastructure.db import engine
from infrastructure.orm.base import Base
from tests.fakes.fiscal_data import fiscal_party_payload


@pytest.fixture(scope="session", autouse=True)
def _ensure_schema():
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_db():
    # Runs before every test: repositories open/commit/close their own session
    # per call (no shared transaction to roll back), so isolation is done via
    # TRUNCATE rather than a SAVEPOINT/rollback strategy.
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE TABLE invoice_attempts, invoices, merchants, recipients RESTART IDENTITY CASCADE")
        )
    yield


@pytest.fixture
def fake_redis():
    return fakeredis.FakeStrictRedis()


@pytest.fixture
def client(fake_redis):
    main.container.redis_conn.override(fake_redis)
    main.container.invoice_queue.override(Queue(name="invoices", connection=fake_redis, is_async=False))
    with TestClient(main.app) as test_client:
        yield test_client
    main.container.reset_override()


@pytest.fixture
def set_fixed_provider():
    # Bypasses the registry entirely: every country_code resolves to this one
    # provider, so failure/retry tests can inject a fixed `fault_injector`.
    def _set(provider):
        main.container.invoice_service.override(
            di_providers.Factory(
                InvoiceService,
                invoice_repo=main.container.invoice_repo,
                attempt_repo=main.container.attempt_repo,
                merchant_repo=main.container.merchant_repo,
                recipient_repo=main.container.recipient_repo,
                queue=main.container.invoice_queue,
                provider_factory=di_providers.Object(lambda country_code: provider),
                provider_invoker=main.container.provider_invoker,
                job_timeout=60,
            )
        )

    return _set


def register_merchant(client, country_code: str, **overrides) -> str:
    # `overrides` forward to fiscal_party_payload, e.g. `extra={}` to build a
    # merchant missing a required field, for validation tests.
    resp = client.post(
        "/merchants",
        json={"country_code": country_code, "fiscal_party": fiscal_party_payload(country_code, **overrides)},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["merchant_id"]


def register_recipient(client, country_code: str, **overrides) -> str:
    # Mirror of register_merchant.
    resp = client.post(
        "/recipients",
        json={"country_code": country_code, "fiscal_party": fiscal_party_payload(country_code, **overrides)},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["recipient_id"]


def corrupt_extra_fields(table: str, row_id: str) -> None:
    # Bypasses the API's registration-time validation on purpose, to simulate
    # data drift and exercise the defense-in-depth revalidation in
    # InvoiceProvider.validate_fiscal_data.
    assert table in ("merchants", "recipients")
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE {table} SET extra = '{{}}'::jsonb WHERE id = CAST(:id AS uuid)"),
            {"id": row_id},
        )
