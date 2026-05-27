# Tax Agent

AI-powered tax preparation agent for India and US tax regimes. Ingests salary slips, Form-16, W-2, investment documents, calculates liability via a deterministic engine, recommends the correct ITR form, and generates filings with optimization suggestions.

**Disclaimer**: This tool assists with tax estimation and document organization. It is not legal advice, not a substitute for a CA/CPA, and does not e-file returns.

---

## Architecture

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI, SQLAlchemy 2.0, aiosqlite |
| Frontend | Next.js (planned) |
| LLM | Ollama (local, Phase 2+) |
| Database | SQLite → PostgreSQL |
| Desktop (Phase 6) | Tauri shell |

## Quick Start

```bash
cd backend
uv sync            # install dependencies
uv run uvicorn app.main:create_app --factory --reload
```

API docs at `http://localhost:8000/docs`.

## Project Structure

```
backend/           FastAPI API (current work)
  app/
    api/           Routers (auth, data, upload, calculation)
    core/          Security, exceptions, logging, permissions
    schemas/       Pydantic models
    tax_engine/    Deterministic calculation engine
    config.py      pydantic-settings
  db/              SQLAlchemy models, session, migrations
  tests/
frontend/          Next.js app (planned)
```

## Development

See [backend/README.md](backend/README.md) for backend setup and [plan.md](plan.md) for the full implementation roadmap.
