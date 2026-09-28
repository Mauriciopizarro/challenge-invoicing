from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import infrastructure.orm  # noqa: F401 -- registers ORM classes on Base before create_all
from domain.exceptions.idempotency_conflict import IdempotencyConflict
from domain.exceptions.invalid_fiscal_data import InvalidFiscalDataError
from domain.exceptions.invoice_not_found import InvoiceNotFoundError
from domain.exceptions.merchant_not_found import MerchantNotFoundError
from domain.exceptions.recipient_not_found import RecipientNotFoundError
from domain.exceptions.unsupported_country import UnsupportedCountryError
from infrastructure.controllers import (
    health_controller,
    invoice_controller,
    merchant_controller,
    provider_controller,
    recipient_controller,
)
from infrastructure.db import engine
from infrastructure.injector import container
from infrastructure.orm.base import Base

app = FastAPI(
    title="Multi-Country Invoicing Service",
    description="Routes invoices to per-country provider adapters, with retry, idempotency, and audit trail.",
    version="1.0",
)
app.container = container
container.wire(modules=[invoice_controller, merchant_controller, recipient_controller, provider_controller])


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


@app.exception_handler(UnsupportedCountryError)
def handle_unsupported_country(request: Request, exc: UnsupportedCountryError):
    return _error_response(422, "unsupported_country", str(exc))


@app.exception_handler(InvoiceNotFoundError)
def handle_invoice_not_found(request: Request, exc: InvoiceNotFoundError):
    return _error_response(404, "invoice_not_found", str(exc))


@app.exception_handler(IdempotencyConflict)
def handle_idempotency_conflict(request: Request, exc: IdempotencyConflict):
    return _error_response(409, "idempotency_conflict", str(exc))


@app.exception_handler(MerchantNotFoundError)
def handle_merchant_not_found(request: Request, exc: MerchantNotFoundError):
    return _error_response(404, "merchant_not_found", str(exc))


@app.exception_handler(InvalidFiscalDataError)
def handle_invalid_fiscal_data(request: Request, exc: InvalidFiscalDataError):
    return _error_response(422, "invalid_fiscal_data", str(exc))


@app.exception_handler(RecipientNotFoundError)
def handle_recipient_not_found(request: Request, exc: RecipientNotFoundError):
    return _error_response(404, "recipient_not_found", str(exc))


app.include_router(invoice_controller.router, prefix="/invoices", tags=["Invoices"])
app.include_router(merchant_controller.router, prefix="/merchants", tags=["Merchants"])
app.include_router(recipient_controller.router, prefix="/recipients", tags=["Recipients"])
app.include_router(provider_controller.router, prefix="/providers", tags=["Providers"])
app.include_router(health_controller.router, tags=["Health"])
