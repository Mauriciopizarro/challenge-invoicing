# Multi-Country Invoicing Service

A Python service that issues invoices across multiple countries by routing each
request to the correct per-country provider adapter, with configurable
timeout/retry per provider, a race-safe idempotency guarantee, and a full audit
trail of every attempt made.

**Stack:** FastAPI · Pydantic v2 · SQLAlchemy 2.0 · PostgreSQL · Redis + RQ ·
`dependency-injector` · `tenacity` · pytest.

## Architecture

```mermaid
flowchart LR
    Client([Client])

    subgraph API_Process["app (FastAPI)"]
        MC[merchant_controller]
        RC[recipient_controller]
        API[invoice_controller]
        Registry[[Provider Registry]]
    end

    subgraph Worker_Process["worker (RQ SimpleWorker)"]
        Job[process_invoice_job]
        Invoker[ProviderInvoker\ntenacity retry/backoff]
        Adapter[Provider Adapter\nAR = AFIP · BR = NFe · MX = SAT]
    end

    DB[(PostgreSQL\nmerchants / recipients / invoices / invoice_attempts)]
    Q[(Redis\nRQ queue)]

    Client -- "POST /merchants\n(issuer fiscal identity, once)" --> MC
    MC -- "validate + save" --> DB

    Client -- "POST /recipients\n(recipient fiscal identity, once)" --> RC
    RC -- "validate + save" --> DB

    Client -- "POST /invoices\nIdempotency-Key,\nissuer_merchant_id, recipient_id" --> API
    API -- "look up merchant + recipient\nderive country_code" --> DB
    API -- "resolve provider" --> Registry
    API -- "1. save invoice as pending\n(issuer + recipient snapshots)" --> DB
    API -- "2. enqueue invoice_id" --> Q
    API -- "202 {status: pending}" --> Client

    Q --> Job
    Job -- "mark processing" --> DB
    Job --> Invoker
    Invoker --> Adapter
    Invoker -- "record every attempt" --> DB
    Job -- "mark issued / failed" --> DB

    Client -- "GET /invoices/{id}" --> API
    API -- "read invoice + attempts" --> DB
```

The invoice gets written to Postgres as `pending` **before** anything is
enqueued, and the RQ worker runs as a separate process on the same codebase.
`POST /invoices` never calls a provider inline. It only resolves *which*
provider handles the invoice (a pure routing decision derived from the
issuing merchant), then persists and enqueues.

### Layout

```
domain/            Pure domain: Invoice / InvoiceAttempt / Merchant / Recipient /
                    FiscalParty models, value objects, repository + provider
                    interfaces, typed exceptions.
application/        InvoiceService, MerchantService, RecipientService (use
                    cases) and ProviderInvoker (retry+audit).
infrastructure/
  providers/        Provider adapters, registry, auto-discovery, factory.
  orm/, repositories/, db.py   SQLAlchemy persistence.
  queue/            Redis connection + the RQ job entrypoint.
  controllers/      FastAPI routers + request/response DTOs.
  injector.py        dependency-injector container (shared by app and worker).
tests/              pytest: integration (API + DB + fake Redis) and unit.
```

## Running it

```bash
docker-compose up --build
```

This starts `db` (Postgres), `redis`, `app` (FastAPI on `:8000`), and `worker`
(RQ worker). `healthcheck` plus `depends_on: condition: service_healthy`
wires them together: no manual steps, no migrations (the app creates tables
from ORM metadata on startup).

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`, or the committed snapshot
  at [`openapi.json`](./openapi.json) (regenerate with
  `python scripts/generate_openapi.py`).

### Try it

```bash
# 1. Register the issuing merchant once. Every invoice it issues reuses this
#    fiscal identity, and its country_code routes the invoice.
curl -X POST http://localhost:8000/merchants \
  -H "Content-Type: application/json" \
  -d '{"country_code": "AR", "fiscal_party": {"legal_name": "Acme Argentina SA", "tax_id": {"id_type": "CUIT", "value": "30-12345678-9"}, "address": "Av. Corrientes 1234, CABA", "extra": {"condicion_iva": "Responsable Inscripto"}}}'
# -> 201 {"merchant_id": "...", "country_code": "AR", "fiscal_party": {...}, "created_at": "..."}

# 2. Register the recipient once too, same shape as a merchant. Every invoice
#    to that customer reuses it instead of resending the data each time.
curl -X POST http://localhost:8000/recipients \
  -H "Content-Type: application/json" \
  -d '{"country_code": "AR", "fiscal_party": {"legal_name": "Cliente SRL", "tax_id": {"id_type": "CUIT", "value": "20-98765432-1"}, "address": "San Martin 500, Rosario", "extra": {"condicion_iva": "Responsable Inscripto"}}}'
# -> 201 {"recipient_id": "...", "country_code": "AR", "fiscal_party": {...}, "created_at": "..."}

# 3. Issue an invoice referencing both ids. country_code, currency, issuer,
#    and recipient fiscal data never travel inline here; the service derives
#    or looks up all four from the two registrations above.
curl -X POST http://localhost:8000/invoices \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: order-42" \
  -d '{"entity_id": "cust-1", "amount": 1500.00, "issuer_merchant_id": "<merchant_id>", "recipient_id": "<recipient_id>"}'
# -> 202 {"invoice_id": "...", "status": "pending", "provider_used": "AFIP", "external_reference": null}

curl http://localhost:8000/invoices/<invoice_id>
# -> status: "issued", external_reference set, issuer/recipient fiscal data,
#    and the full attempts audit trail

curl http://localhost:8000/providers
# -> [{"country_code": "AR", "provider": "AFIP"}, {"country_code": "BR", "provider": "NFe"}, {"country_code": "MX", "provider": "SAT"}]
```

### Tests

```bash
docker-compose up -d db
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/invoicing pytest
```

Tests run against a real Postgres (for native `UUID`/`JSONB` columns) but use
`fakeredis` for the queue, so no live Redis is needed. 53 tests cover: happy
path for AR/BR, permanent provider failure, transient failure that exhausts
retries, transient failure that recovers, the real async contract (queue left
fully async, drained with `SimpleWorker(...).work(burst=True)`),
sequential and concurrent idempotent replay, input validation, merchant and
recipient registration and correction (including rejecting
incomplete/wrong-type/role-specific fiscal data and unsupported countries),
invoice fiscal validation (missing recipient field, mismatched tax id type,
the defense-in-depth issuer revalidation, and confirming that correcting
either a merchant or a recipient never rewrites an already-issued invoice's
fiscal snapshot, see Technical decisions), and the `ProviderInvoker`
retry/audit logic and `Invoice` state machine in isolation.

## Adding a new country/provider

No file outside `infrastructure/providers/` needs to change:

1. Create `infrastructure/providers/uy_provider.py`.
2. Subclass `InvoiceProvider` (`domain/interfaces/invoice_provider.py`),
   implement `send_invoice`, and set `name`, `timeout_seconds`, `max_retries`,
   `backoff_base`, `backoff_max`, `EXPECTED_TAX_ID_TYPES`,
   `ISSUER_REQUIRED_EXTRA_FIELDS`/`RECIPIENT_REQUIRED_EXTRA_FIELDS` for that
   country's well-known fiscal fields.
3. Decorate the class with `@register_provider("UY")`.

```python
# infrastructure/providers/uy_provider.py
from domain.interfaces.invoice_provider import InvoiceProvider, ProviderRequest, ProviderResponse
from infrastructure.providers.registry import register_provider

@register_provider("UY")
class UruguayInvoiceProvider(InvoiceProvider):
    name = "DGI"
    timeout_seconds = 4.0
    max_retries = 3
    EXPECTED_TAX_ID_TYPES = frozenset({"RUT"})
    ISSUER_REQUIRED_EXTRA_FIELDS = RECIPIENT_REQUIRED_EXTRA_FIELDS = ("giro",)

    def send_invoice(self, request: ProviderRequest) -> ProviderResponse:
        self.validate_fiscal_data(request.issuer, request.recipient, regulator_name="DGI")
        ...
```

`infrastructure/providers/__init__.py` auto-imports every module in that
package on startup (`pkgutil.iter_modules`), which runs the `@register_provider`
decorator and populates the registry. `InvoiceService`, `MerchantService`,
the controllers, and `Injector` never reference a country code directly, so
none of them change. `GET /providers`, the `country_code` validation on
`POST /merchants`, and each provider's own fiscal-field requirements all read
from the same per-provider declarations.

## Fiscal identity: issuers and recipients

Every invoice carries two full fiscal identities, `issuer` and `recipient`
(`domain/models/fiscal_party.py`), because AFIP/ARCA, SAT, and NF-e legally
require both to issue a real invoice: `legal_name`, a `tax_id` (type + value,
e.g. `CUIT`/`RFC`/`CNPJ`), an `address`, and a small `extra` bag of the
well-known fields each country asks for (not an exhaustive catalog):

| Country | `tax_id.id_type` | `extra` fields |
|---|---|---|
| AR (AFIP/ARCA) | `CUIT` | `condicion_iva` |
| MX (SAT) | `RFC` | `regimen_fiscal` (issuer + recipient), `codigo_postal` (recipient only, CFDI 4.0 "Domicilio Fiscal Receptor") |
| BR (NF-e/SEFAZ) | `CNPJ` or `CPF` | `inscricao_estadual` |

**Issuer = `Merchant`, multi-tenant, registered once.** `POST /merchants`
registers a tenant's fiscal identity. `POST /invoices` references it by
`issuer_merchant_id`, and the service derives `country_code` from the
merchant instead of accepting it per invoice (see Technical decisions).
**Deliberately no authentication**: the service trusts `issuer_merchant_id`
as given in the body. Production code would derive it from an authenticated
principal (API key/JWT) instead, never a client-supplied id (see below).

**Correcting a merchant's fiscal data: `PUT /merchants/{merchant_id}`.** It
takes the same `fiscal_party` shape as registration (full replace, validated
with the same rules). `country_code` isn't part of the body: fixing a typo in
a tax id and re-jurisdictioning a legal entity are different operations (see
the `Merchant` invariant above). Invoices already issued under the old data
stay unaffected, because each invoice stores `issuer` as a snapshot rather
than a live reference to the merchant
(`test_correcting_a_merchant_does_not_change_already_issued_invoices`).

**Recipient = `Recipient`, also registered once, also global.**
`POST /recipients` mirrors `POST /merchants` almost exactly: same
`FiscalParty` shape, same fail-fast validation on registration/update
(`PUT /recipients/{recipient_id}`), same JSONB snapshot on the invoice, so a
correction here never rewrites a past invoice either
(`test_correcting_a_recipient_does_not_change_already_issued_invoices`).
`POST /invoices` references it by `recipient_id` instead of resending the
full fiscal identity on every invoice. There's still no "consumidor final"
fallback (a `Recipient` is always required in full), because this is a B2B
platform (that concept is a B2C exception in AFIP, not applicable here).
`Recipient` has its own `country_code` too, which determines which
provider's rules validate it at registration, but it is **not** owned by a
specific `Merchant` (see Technical decisions for why).

## Technical decisions

**Layered/hexagonal architecture (domain / application / infrastructure)
with FastAPI + SQLAlchemy + `dependency-injector`.** This mirrors a proven
pattern instead of inventing a new one for a time-boxed challenge, and maps
cleanly onto the "extensible without touching the core" requirement: the
provider contract lives in `domain/`, adapters live in `infrastructure/`, and
`application/` never imports a concrete provider.

**Idempotency via an explicit `Idempotency-Key` header and a DB unique
constraint, no derived key.** A key derived from
`entity_id+amount+currency+country_code` would silently collapse two
*legitimate* same-amount invoices for the same entity on the same day.
Requiring the client to supply the key (Stripe's convention) turns "this is a
retry of that exact request" into an explicit statement instead of a guess.
The DB constraint provides the actual safety: `save_new` attempts a plain
`INSERT`; a duplicate key raises `IntegrityError`, the code translates that
to `IdempotencyConflict`, and the service looks up and returns the
already-committed row. Two concurrent requests with the same key both race to
insert, and Postgres guarantees exactly one wins, so the guarantee holds
under real concurrency as well as sequential retries (see
`test_idempotent_replay_is_safe_under_concurrent_requests`).

**Async processing via Redis Queue (RQ) over FastAPI `BackgroundTasks` or
Celery.** `BackgroundTasks` runs in-process and doesn't survive an app
restart. A crash between "provider confirmed" and "we noted that" would lose
the invoice entirely, exactly the failure mode this challenge asks to
resist. Celery is the heavier standard choice, but for two lightweight
simulated adapters and a single queue, RQ's simplicity fit the scope better:
a single `Queue`/`Worker` primitive, no separate broker beyond Redis, and a
trivial override with `fakeredis` in tests. Writing the invoice as `pending`
**before** the job is enqueued is what protects against "confirmation
without persistence": if the process died right after the provider call
succeeded, the invoice record already exists in `pending`/`processing`, so
nothing gets silently lost (see the residual-risk note below for what this
doesn't fully solve).

**`SimpleWorker` (no fork) instead of RQ's default forking `Worker`.** RQ's
default worker forks a child process per job; if the SQLAlchemy `Engine`
(and its connection pool) was created before the fork, the child inherits
the same underlying socket file descriptors, a known SQLAlchemy-across-fork
hazard. `SimpleWorker` runs jobs in-process instead, at the cost of no
per-job crash isolation. That's an acceptable trade here, and the same class
doubles as what the test uses to prove the real async contract
(`test_post_returns_pending_before_worker_processes_it`).

**A shared `dependency-injector` container as a module-level singleton
inside `infrastructure/injector.py`, rather than built in `main.py`.** The
RQ worker process imports `infrastructure.queue.jobs`, never `main.py`, so
the container had to live somewhere both processes reach. This produced a
real gotcha: giving the container a `wiring_config` that lists the
controller modules, while those same controllers import `Injector` from
that same `injector.py`, creates a circular import. `Injector()`'s
auto-wiring re-enters `injector.py` mid-import, tries to wire a controller
module that is *also* still mid-import, and ends up wiring against an
empty, half-loaded module, so it silently injects nothing. That surfaced at
runtime as `AttributeError: 'Provide' object has no attribute
'create_invoice'`, because FastAPI resolved the unwired
`Depends(Provide[...])` marker itself instead of dependency-injector's
patched wrapper resolving it. The fix: drop `wiring_config` from the
container, and have `main.py` call `container.wire(...)` directly, after the
controller modules are already fully imported. The container object itself
stays a cheap, side-effect-free singleton that the worker can import safely.

**`tenacity` for retry/backoff, configured per-provider, with audit logging
inside the wrapped call rather than tenacity's `before`/`after` hooks.**
Timeout, `max_retries`, and backoff live as class attributes on each
`InvoiceProvider` subclass (AR: 3s/3 retries, BR: 5s/4 retries; different
providers, different reliability profiles, no branching in the core).
`ProviderTransientError` gets retried; `ProviderPermanentError` never does.
The audit trail needed **every** attempt, including the terminal one, but
tenacity's `after` hook only fires when it has already decided to retry,
never on the attempt that ends the loop (success or a permanent failure). A
first implementation using `before`/`after` silently dropped the log row for
every successful call and every permanent failure. Wrapping the call itself,
and logging inside that wrapper on both the success and the exception path,
fixed it. The unit tests in `tests/unit/test_provider_invoker.py` caught
this before it ever reached the API layer.

**Simulated adapters run in-process with an injectable `fault_injector`,
instead of mock HTTP servers.** A `fault_injector: Callable[[], None] | None`
constructor arg (`None` in production) gives tests a deterministic way to
force a transient/permanent failure N times, without magic values baked into
request payloads and without standing up an HTTP mock server for two
adapters that don't talk HTTP in the first place.

**`Decimal`/`Numeric(12,2)` for money, not `float`.** Floating-point rounding
error on monetary amounts is a correctness bug waiting to happen. It's an
easy default to get wrong, so this decision gets called out here on purpose.

**Postgres for tests (via `docker-compose up -d db`), not SQLite or
`testcontainers-python`.** The schema uses Postgres-native `UUID` and
`JSONB` columns for the audit payloads; SQLite would need dialect shims for
both, for a challenge-scoped test suite. `testcontainers-python` would
remove the one manual step (`docker-compose up -d db` before `pytest`), at
the cost of an extra dependency and Docker-socket access during test runs.
That trade-off would pay off more on a longer-lived project.

**A fourth `processing` status, beyond the `issued|pending|failed` in the
brief.** The worker sets it the instant it picks up the job, before calling
the provider. It buys observability ("queued but not started" vs. "actively
retrying") and doubles as a guard: `process_invoice` only acts on a
`pending` invoice, so a job delivered twice (say, an RQ worker restart)
becomes a no-op the second time, and the audit trail never gets a spurious
duplicate attempt.

**Known residual risk: the window between "provider confirmed" and "we
recorded it" shrinks close to zero, but doesn't fully close.** Each attempt
gets persisted in its own short transaction immediately after the provider
call returns, so the gap stays small. It isn't zero, because these adapters
are simulated and don't expose an idempotent "check status by reference"
call the way a real AFIP/NF-e integration would. If the worker process died
in that exact window, an invoice could get stuck in `processing` with no
attempt recorded for the call that succeeded upstream. The mitigation: never
auto-retry a `processing` invoice from a fresh request, since retrying
blindly here recreates the double-billing risk this challenge tests for, and
treat a `processing` invoice older than some threshold as a signal for
manual reconciliation instead of automated action. A full write-ahead
log/outbox on top of that fell outside the scope of a take-home; documenting
the boundary seemed more honest than pretending it doesn't exist.

**Multi-tenant issuer (`Merchant`), deliberately without authentication.**
Multi-tenancy and authentication are separate concerns. Multi-tenancy means
the issuer's fiscal identity is looked-up data instead of a config constant
(`POST /merchants` once, referenced by id afterward); it doesn't by itself
require login. Authentication is the separate question of *proving* who's
calling, which real production code would need: deriving
`issuer_merchant_id` from an authenticated API key/JWT, never trusting a
client-supplied value (otherwise anyone who learns another merchant's id
could invoice on their behalf). Building real auth wasn't part of this
challenge's evaluation criteria, so this scopes it out on purpose and
documents it here rather than skipping it silently.

**`Recipient` is a global directory, not owned by a specific `Merchant`.**
The realistic real-world model gives each merchant its own book of customers
(`recipients` scoped to an `issuer_merchant_id`); this project considered
that and rejected it for this scope. Without real authentication (previous
decision), an ownership boundary here would enforce nothing: any request can
already pass any `issuer_merchant_id` it wants, so "recipients belong to
merchants" would be a security boundary in appearance only, while adding
real modeling weight (an extra FK, and a check in
`InvoiceService.create_invoice` that a given `recipient_id` "belongs to" the
calling merchant, itself bypassable by passing a different
`issuer_merchant_id`). A global directory stays simpler, mirrors `Merchant`
exactly, and matches what the current auth story can guarantee. Real
authentication and per-merchant recipient ownership belong together as a
pair; this README documents that pairing rather than building half of it.

**`Recipient` has its own `country_code`, to reuse `Merchant`'s fail-fast
registration validation; it does not restrict which invoices a recipient can
be used for.** `POST /recipients` needs *some* provider to validate against
(`RECIPIENT_REQUIRED_EXTRA_FIELDS` for that country), the same way
`POST /merchants` does. A `Recipient`'s `country_code` is never compared
against the invoice's `country_code` at creation time. The real
compatibility check remains `InvoiceProvider.validate_fiscal_data` at
`send_invoice` (defense in depth, the same mechanism already built for the
issuer). Registering a recipient as MX and then using it on an AR invoice
gets accepted at submission (`202`) and only fails, with a clear reason,
when the worker tries to invoice through AFIP
(`test_recipient_tax_id_type_mismatch_marks_invoice_failed`), consistent
with how every other fiscal-rule violation in this service surfaces.

**`country_code` is derived from the issuing `Merchant`, not chosen per
invoice.** The tax authority you report to is the issuer's own jurisdiction:
an AR company invoicing a BR customer still reports to AFIP/ARCA, not
Brazil's SEFAZ. It isn't a free choice per request, and deriving it this way
also closes a real validation gap. Earlier, nothing stopped a client from
sending `country_code: "BR"` alongside data belonging to an AR merchant.
**Invariant**: one `Merchant` equals one legal entity equals one
`country_code`. A company operating in several countries gets modeled as
several `Merchant` records (one per jurisdiction), not one merchant with a
variable country. **Known limitation, out of scope on purpose**:
destination-based VAT schemes (e.g. the EU's OSS, where the issuer reports
in the *buyer's* country) break this invariant. None of AR/MX/BR work that
way, so it doesn't apply here; naming it keeps the gap intentional instead
of looking like an oversight.

**`currency` is derived too, from the resolved provider
(`InvoiceProvider.EXPECTED_CURRENCY`), never accepted in the request body.**
A country has exactly one valid invoicing currency, so letting the client
supply it only added a way to be wrong (or lie) without adding any real
choice, the same reasoning behind deriving `country_code`. The mismatch
check that used to validate a client-supplied currency against the provider
still lives in each adapter's `send_invoice`, but its purpose changed. Since
the value can no longer be wrong at submission time, it now guards only
against `invoice.currency` (fixed at creation time) drifting from the
*current* `provider.EXPECTED_CURRENCY` (read at processing time), the same
defense-in-depth reasoning already applied to the issuer's fiscal data
above. This check earns its keep; it isn't leftover code.

**The worker validates recipient fiscal data asynchronously, not at `POST`
time.** An incomplete `recipient` doesn't produce a `422` on submission. It
gets a `202 pending` like always, and the invoice ends up `failed` with a
human-readable `failure_reason` naming the exact missing field (e.g. *"AFIP
requires the recipient's fiscal field(s) condicion_iva, which are
missing"*), visible via `GET`. This mirrors how currency mismatches already
worked before this feature existed: it's the provider's business rule
rather than a request-schema concern, so it lives in
`infrastructure/providers/*.py` (`InvoiceProvider.validate_fiscal_data`)
instead of the shared DTO. Country-specific rules stay out of the core, the
same way currency validation always has.

**Issuer fiscal data gets validated in two places.** `POST /merchants`
rejects incomplete fiscal data up front (fail-fast, `422
invalid_fiscal_data`, before the merchant ever exists). `send_invoice`
*also* revalidates the issuer with the exact same check used for the
recipient (`test_issuer_with_drifted_incomplete_fiscal_data_marks_invoice_failed`
simulates this by mutating a merchant's data directly at the DB, bypassing
the API on purpose). This is deliberate belt-and-suspenders. Registration-time
validation only proves the data was complete *at that moment*; if a
country's required fields changed after older merchants were already
registered, single-point validation would let a broken issuer slip all the
way to a failed provider call with no clear signal. Revalidating costs a
few lines (the same `missing_fiscal_fields` helper already built for the
recipient) and turns that scenario into a `failed`-with-clear-reason invoice
instead of an unexplained crash.

**Registration and update validation reuse the provider's own rule engine
(`InvoiceProvider.fiscal_data_problem`).** Adding the `PUT /merchants/{id}`
endpoint surfaced a real gap: `register_merchant` checked only
`ISSUER_REQUIRED_EXTRA_FIELDS` (missing fields), never
`EXPECTED_TAX_ID_TYPES`. A merchant registered with, say, an RFC instead of
a CUIT would sail through `POST /merchants` and only fail later, on its
first real invoice. Extracting `validate_fiscal_data`'s two rules (tax id
type, required fields) into a single-party `fiscal_data_problem` method that
both `send_invoice` and `MerchantService` call fixed the gap. Registration,
update, and invoicing can no longer disagree about what "valid" means for a
country, because exactly one place decides.

**`FiscalParty`/`TaxId` shape: common fields plus a per-provider `extra`
bag, rather than a strongly-typed subclass per country.** `tax_id.id_type`
is a free string instead of a closed Enum, and `extra` is `dict[str, str]`
rather than `ArgentinaFiscalParty`/`MexicoFiscalParty` subclasses. A closed
schema would force editing shared domain code every time a country's
regulator adds or changes a field, exactly the coupling the provider
registry already exists to avoid. Each adapter declares and validates the
keys *it* needs (`EXPECTED_TAX_ID_TYPES`, `*_REQUIRED_EXTRA_FIELDS`), and
the shared model stays generic.

**`issuer`/`recipient` live as JSONB snapshots on the invoice, instead of a
live join to `merchants`/`recipients`.** `issuer_merchant_id` (and
`recipient_id`) stay as foreign keys for traceability (e.g. "every invoice
this merchant issued"), but the invoice's own `issuer`/`recipient` columns
are copies taken at creation time. An invoice is a legal document of a
point in time. If a merchant edits its registered address next month,
invoices already issued must not silently change to reflect that. The same
reasoning already applies to
`invoice_attempts.request_payload`/`response_payload` elsewhere in this
project.
