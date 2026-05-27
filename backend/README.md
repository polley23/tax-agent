# Tax Agent Backend

FastAPI service for the cross-border tax calculation platform. Implements Phase 1 of the [implementation plan](../plan.md).

## Quick Start

```bash
cd backend

# Using uv (recommended)
uv sync
uv run uvicorn app.main:create_app --factory --reload

# Or with a venv
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:create_app --factory --reload
```

API docs at `http://localhost:8000/docs`.

## Structure

```
backend/
├── app/
│   ├── api/          # FastAPI routers (auth, data, upload, calculation, health)
│   ├── config.py     # Settings (pydantic BaseSettings)
│   ├── core/
│   │   ├── events.py       # In-process event bus
│   │   ├── exceptions.py   # Domain errors + global handlers
│   │   ├── logging.py      # Structured JSON logging
│   │   ├── perm.py         # Resource ownership guard
│   │   └── security.py     # Password hashing, JWT tokens
│   ├── main.py       # Application factory
│   ├── schemas/      # Pydantic request/response models
│   └── tax_engine/   # Deterministic calculation engine (Phase 2)
├── db/
│   ├── models.py     # SQLAlchemy models (8 P1 tables)
│   └── session.py    # Async engine / session factory
├── mocks/            # JSON files for non-authorised endpoints
├── tests/
├── pyproject.toml
└── README.md
```

## Authentication

Register and login via `/auth/register` and `/auth/login` to obtain a JWT. Include it on every data endpoint:

```bash
Authorization: Bearer <token>
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/auth/register` | Create user |
| POST | `/auth/login` | Login, receive JWT |
| POST | `/profile` | Create profile |
| GET | `/profile` | Get profile |
| POST | `/income` | Add income source |
| GET | `/income` | List income sources |
| GET | `/income/{id}` | Get income source |
| DELETE | `/income/{id}` | Delete income source |
| POST | `/deductions` | Add deduction |
| GET | `/deductions` | List deductions |
| GET | `/deductions/{id}` | Get deduction |
| DELETE | `/deductions/{id}` | Delete deduction |
| POST | `/documents/upload` | Upload document |
| GET | `/documents` | List documents |
| GET | `/documents/{id}` | Get document metadata |
| GET | `/documents/{id}/download` | Download document |
| DELETE | `/documents/{id}` | Delete document |
| POST | `/documents/purge` | Purge all documents |
| POST | `/calculation` | Trigger tax calculation |

## Database

SQLite by default via `aiosqlite`. Data directory: `~/.local/share/tax-agent/`. Override with `DATABASE_URL` in `.env`.

Alembic migrations in `alembic/`. Apply pending migrations:

```bash
uv run alembic upgrade head
```

## Testing

```bash
uv run python3 -m pytest --asyncio-mode=auto -q
```

## Configuration

Copy `.env.example` to `.env` and adjust. All settings validated via pydantic-settings.

```bash
DATABASE_URL=sqlite+aiosqlite:///~/.local/share/tax-agent/tax_agent.db
DEBUG=true
SECRET_KEY=change-me
LOG_LEVEL=debug
LOG_JSON=false
JWT_SECRET=your-jwt-secret
JWT_EXPIRE_MINUTES=1440
```
