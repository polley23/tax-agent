# Tax Agent Backend

Dual-jurisdiction (US/UK) tax preparation agent backend built with FastAPI, SQLAlchemy, and SQLite.

## Architecture

- **FastAPI** app factory in `backend/app/main.py` with security headers middleware, CORS, and trusted-host guard
- **SQLAlchemy 2.0** async ORM (aiosqlite) — 8 Phase-1 tables: User, Profile, TaxYear, IncomeSource, Deduction, Document, TaxCalculation, TaxReturn
- **Pydantic v2** schemas in `backend/app/schemas/` for request/response validation
- **JWT auth** via bcrypt password hashing and python-jose tokens. All data endpoints require `Bearer <token>` header
- **Rule-pack engine** in `backend/app/tax_engine/` — deterministic, pure-function tax calculation per financial year (Phase 2, currently stub)
- **Alembic** migrations in `backend/alembic/` for schema versioning
- Data directory: `~/.local/share/tax-agent/` (SQLite DB and uploads)

## Key Conventions

- **Auth**: `get_current_user` dependency injects the authenticated `User` model. `require_owner(Model)` verifies resource ownership via `{id}` path param
- **Routing**: All sub-routers aggregated in `backend/app/api/__init__.py`. Endpoints grouped by domain: health, auth, data (profile/income/deductions), upload, calculation
- **Exceptions**: Custom `TaxAgentError` hierarchy in `app/core/exceptions.py` with global handlers. Domain errors return structured JSON with `detail` and `code` fields
- **Logging**: structlog configured in `app/core/logging.py`
- **Settings**: pydantic-settings via `app/config.py` — env vars or `.env` file
- **Testing**: pytest + pytest-asyncio (`asyncio_mode = "auto"`). Tests in `backend/tests/`
- **No comments in code** unless the why is non-obvious. Rely on descriptive identifiers

## Dependencies

- FastAPI, uvicorn, SQLAlchemy 2.0, alembic, Pydantic v2, structlog
- bcrypt, python-jose (auth)
- python-multipart (file uploads)
- aiosqlite (async SQLite driver)
- Dev: pytest, pytest-asyncio, httpx, coverage

## What's Wired vs Stubbed

**Wired (Phase 1):** Health check, auth (register/login), profile CRUD, income/deduction CRUD, document upload, JWT middleware, security headers, exception handling, DB session management

**Stubbed (Phase 2+):** Tax engine (`calculate_tax`, `load_rule_pack`, `validate_brackets`) raises `NotImplementedError`. Document parsing, PDF generation, tax return filing, continuous tax intelligence, Ollama LLM integration

## Permitted Actions

- Run tests, start dev server, read/write files in `backend/`
- Commit and push to git
- Run pytest with `python3 -m pytest --asyncio-mode=auto -q`
