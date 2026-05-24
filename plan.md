# Dual-Jurisdiction Tax Agent — Implementation Plan

## Context
Greenfield project in `/home/saptarshi/tax-agent/`. You want an AI-powered web app that ingests your financial documents (salary, RSU, stocks, investments), understands Indian + US tax rules, reasons over your situation via a local LLM, and generates tax filings with optimization recommendations.

**Tech stack**: Next.js (frontend) + FastAPI (backend) + LangChain + Ollama (local LLM) + SQLite → PostgreSQL

**Prior-year support**: Upload a Form-16, W-2, or prior-year tax document and run the tax engine against the **financial year encoded in that document** (not only the current filing year). Rule packs and slab tables are versioned per FY so historical reconciliation and year-over-year comparison are first-class.

**Continuous tax intelligence**: While the backend is running and online, a background worker polls official India RSS feeds (and fallback publishers), deduplicates items, and writes **staging** RAG updates by feed priority; production indexes promote only after review. Numeric tax always comes from `rule_versions.py`, not RAG.

**TurboTax-style mocks**: Development and CI use curated scenario fixtures (synthetic profiles, golden tax outcomes, mock documents, interview checkpoints) so every flow is testable without real PII or live LLM calls.

**Disclaimer**: This tool assists with tax estimation and document organization. It is **not** legal advice, not a substitute for a CA/CPA, and does **not** e-file returns unless explicitly built in a later phase.

---

## MVP scope (v1.0)

| In scope (v1) | Deferred (v1.1+) |
|---------------|-------------------|
| India resident salaried (salary + bank interest + 80C) | Full US 1040 filing workflow |
| Form-16, AIS (JSON first), 26AS, bank interest certs | FBAR / FATCA (FinCEN 114 / Form 8938) |
| New vs old regime + prior 2 FY reconcile | Auto-promote RAG without human review |
| Background poll of 4 India RSS feeds → DB + UI | IRS RSS parity (stub fetcher only) |
| Q&A with citations (statutory RAG + circulars) | Full ITR-2 XML / e-filing export |
| Calculation summary PDF + JSON export | PayExplainer / forecast at full depth |
| TurboTax-style mocks + golden tests | Multi-user SaaS auth |

**Timeline note**: Phases 1–6 as written ≈ **20–26 weeks** for one developer at quality; MVP row above is achievable in **~10–12 weeks**.

---

## Architecture Overview

```
tax-agent/
├── backend/                          # FastAPI + LangChain
│   ├── app/
│   │   ├── main.py                   # FastAPI app entry, router includes
│   │   ├── config.py                 # Settings (ollama endpoint, db URI, etc.)
│   │   ├── db/
│   │   │   ├── base.py               # SQLAlchemy base
│   │   │   ├── session.py            # Engine/session management
│   │   │   └── models.py             # All ORM models
│   │   ├── tax_rules/                # Tax calculation engine
│   │   │   ├── __init__.py
│   │   │   ├── india/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── new_regime.py     # FY 2025-26 new regime slabs
│   │   │   │   ├── old_regime.py     # FY 2025-26 old regime slabs + sections 80C-80U
│   │   │   │   ├── capital_gains.py  # LTCG/STCG for equities, debt funds
│   │   │   │   ├── perquisites.py    # Per-employee stock, HRA, LTA
│   │   │   │   ├── surcharge_cess.py # Surcharge + 4% cess
│   │   │   │   ├── advance_tax.py    # Advance tax instalments (234C)
│   │   │   │   └── residency.py      # Resident / NRI / RNOR logic
│   │   │   ├── us/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── income.py         # Standard deduction, brackets
│   │   │   │   ├── capital_gains.py  # Short/long-term CG rates
│   │   │   │   ├── rsu.py            # RSU vesting, ordinary income, 83(b)
│   │   │   │   ├── ftca.py           # Foreign Tax Credit (Form 1116)
│   │   │   │   └── filing_status.py  # Single/MFJ/MHO/QheadH
│   │   │   ├── dtaa.py               # DTAA analysis, FTC calculation
│   │   │   ├── rule_loader.py        # Load tax rules into RAG from authoritative sources
│   │   │   ├── rule_versions.py      # FY-versioned rule packs (IN FY, US calendar year)
│   │   │   └── optimizer.py          # "old vs new", 83(b) timing, harvest
│   │   ├── core/
│   │   │   ├── logging.py            # Structured logging, correlation IDs
│   │   │   └── metrics.py            # Performance counters, timing hooks
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── llm_client.py         # Ollama + LangChain LLM wrapper
│   │   │   ├── document_parser.py    # PDF/CSV/PDF ingestion, OCR
│   │   │   ├── agents/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── orchestrator.py   # Route tasks; enforce engine vs LLM boundaries
│   │   │   │   ├── parsing_agent.py
│   │   │   │   ├── calculation_agent.py
│   │   │   │   ├── qa_agent.py
│   │   │   │   ├── optimizer_agent.py
│   │   │   │   ├── pay_explainer_agent.py
│   │   │   │   ├── doc_requester_agent.py
│   │   │   │   └── tax_forecaster_agent.py
│   │   │   ├── rag/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── collections.py    # Named stores: statutory | circulars_faq | user_docs
│   │   │   │   ├── vectorstore.py    # ChromaDB persistent collections
│   │   │   │   ├── chunking.py
│   │   │   │   ├── updater.py        # Staging → promote workflow
│   │   │   │   ├── staging.py        # Pending chunks awaiting review
│   │   │   │   └── retriever.py      # Query order: statutory → circulars → user_docs
│   │   │   └── prompts/
│   │   │       ├── parsing_prompts.py
│   │   │       ├── reasoning_prompts.py
│   │   │       └── qa_prompts.py
│   │   ├── news/
│   │   │   ├── __init__.py
│   │   │   ├── background_worker.py  # Always-on poll loop (uptime + internet)
│   │   │   ├── feed_priority.py      # Feed type → RAG action mapping
│   │   │   ├── rss_parser.py         # Parse RSS XML, extract PDF/HTML links
│   │   │   ├── monitors.py           # Health, backoff, gov-site downtime detection
│   │   │   ├── fetchers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── incometax_rss.py  # incometaxindia.gov.in official RSS feeds (primary)
│   │   │   │   ├── taxmann_rss.py    # Taxmann statutory happenings (fallback verify)
│   │   │   │   ├── taxguru_rss.py    # TaxGuru feedburner (fallback alert)
│   │   │   │   ├── irs.gov.py        # IRS notices, revenue procedures
│   │   │   │   └── tax_news_api.py   # Optional: MoneyControl, ET (non-RAG, alerts only)
│   │   │   ├── parser.py             # Normalize news items to structured format
│   │   │   └── relevance.py          # Classify news → relevant tax rule changes
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── docs.py               # Upload, list, parse documents
│   │   │   ├── income.py             # CRUD for income entries
│   │   │   ├── calculation.py        # Run calculation, get results
│   │   │   ├── tax_years.py          # CRUD, from-document, YoY compare
│   │   │   ├── optimization.py
│   │   │   ├── qa.py                 # Chat (SSE streaming)
│   │   │   ├── reports.py            # Summary PDF/JSON (not e-file in v1)
│   │   │   ├── news.py
│   │   │   ├── rag.py                # Status, manual update, staging promote
│   │   │   ├── feedback.py
│   │   │   └── dev.py                # load-scenario (dev only)
│   │   ├── monitoring/
│   │   │   └── health.py             # Health checks, latency summaries
│   │   ├── events/                   # Event-driven architecture for visibility
│   │   │   ├── __init__.py
│   │   │   ├── emitter.py            # Publish events (parsed, calculated, etc.)
│   │   │   └── listeners.py          # React to events (update UI, trigger downstream)
│   │   └── schemas/                  # Pydantic schemas (request/response)
│   │       ├── document.py
│   │       ├── income.py
│   │       ├── tax_result.py
│   │       └── event.py              # Event schema for pipeline tracking
│   ├── mocks/                        # TurboTax-style scenario data (no real PII)
│   │   ├── scenarios/                # Named taxpayer profiles (JSON)
│   │   │   ├── salaried_india_new_regime.json
│   │   │   ├── salaried_rsu_dual_jurisdiction.json
│   │   │   └── prior_year_form16_reconcile.json
│   │   ├── documents/                # Synthetic PDFs/CSVs per doc type
│   │   ├── golden/                   # Expected tax outputs per scenario
│   │   ├── rss/                      # Cached RSS XML snapshots for fetcher tests
│   │   ├── feed_registry.json        # Seed URLs + feed_type + rag_priority for NewsSource
│   │   └── llm/                      # Recorded LLM responses for deterministic CI
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py               # Shared fixtures (db, llm mock, temp uploads)
│   │   ├── tax_rules/
│   │   │   ├── test_new_regime.py    # Slab boundary edge cases
│   │   │   ├── test_old_regime.py    # Section deductions, HRA formulas
│   │   │   ├── test_capital_gains.py # STCG/LTCG, indexation, exemptions
│   │   │   ├── test_us_income.py     # Brackets, standard deduction
│   │   │   ├── test_us_capital_gains.py # 0/15/20%, short-term
│   │   │   ├── test_us_rsu.py        # Vesting, 83(b), withholding
│   │   │   ├── test_dtaa_ftc.py      # FTC limits, separate vs general category
│   │   │   └── test_optimizer.py     # Regime comparison logic
│   │   ├── ai/
│   │   │   ├── test_document_parser.py # Extraction accuracy per doc type
│   │   │   ├── test_parsing_agent.py # Prompt output validation
│   │   │   ├── test_qa_agent.py      # Answer correctness against ground truth
│   │   │   └── test_rag.py           # Retrieval accuracy, recall tests
│   │   ├── api/
│   │   │   ├── test_docs.py          # Upload, parse, delete flow
│   │   │   ├── test_income.py        # CRUD with validation
│   │   │   ├── test_calculation.py   # Integration: full calculation flow
│   │   │   ├── test_optimization.py  # Full optimization pipeline
│   │   │   └── test_qa.py            # Chat with known questions
│   │   ├── news/
│   │   │   ├── test_fetchers.py      # Each RSS fetcher + cached XML fixtures
│   │   │   ├── test_rss_parser.py    # PDF link extraction from item HTML
│   │   │   ├── test_feed_priority.py # Notification vs blog RAG actions
│   │   │   ├── test_background_worker.py # Poll loop, offline skip, dedup
│   │   │   ├── test_parser.py        # Normalization logic
│   │   │   └── test_relevance.py     # Classification accuracy
│   │   ├── mocks/
│   │   │   └── test_scenario_golden.py # TurboTax-style expected outcomes
│   │   ├── integration/
│   │   │   ├── test_end_to_end.py    # Upload → parse → calculate → report
│   │   │   ├── test_rag_update.py    # Load rules → chunk → embed → retrieve
│   │   │   ├── test_news_pipeline.py # Fetch → parse → classify → notify
│   │   │   ├── test_rsu_full.py      # RSU vest → sell → calculate both jurisdictions
│   │   │   ├── test_prior_year.py    # Form-16 FY → correct versioned rule pack
│   │   │   └── test_cross_phase.py   # Interoperability across phases
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                         # Next.js 14+ (App Router)
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                  # Dashboard
│   │   ├── docs/
│   │   │   └── page.tsx              # Document upload & parse
│   │   ├── income/
│   │   │   └── page.tsx              # Income entry form
│   │   ├── calculation/
│   │   │   └── page.tsx              # Tax results & comparison
│   │   ├── optimization/
│   │   │   └── page.tsx              # Recommendations
│   │   ├── qa/
│   │   │   └── page.tsx              # Chat interface
│   │   ├── reports/
│   │   │   └── page.tsx              # Form viewer/download
│   │   ├── news/
│   │   │   └── page.tsx              # Tax news + rule change feed
│   │   └── settings/
│   │       └── page.tsx              # RAG update, preferences, residency status
│   ├── components/
│   │   ├── document-upload.tsx       # Drag-and-drop with progress
│   │   ├── income-form.tsx           # Multi-step, validated, autosave
│   │   ├── tax-chart.tsx             # Recharts for breakdowns
│   │   ├── tax-table.tsx             # Detailed calculation table
│   │   ├── qa-chat.tsx               # Streaming chat
│   │   ├── pipeline-tracker.tsx      # Visual progress for all processes
│   │   ├── event-log.tsx             # Real-time activity feed
│   │   ├── news-card.tsx             # Tax news item
│   │   ├── rag-uploader.tsx          # Load rules + update RAG UI
│   │   ├── regime-comparison.tsx     # Side-by-side comparison
│   │   ├── what-if-scenario.tsx      # Sliders for tax planning
│   │   ├── guided-tour.tsx           # First-time onboarding tour
│   │   ├── documents-checklist.tsx   # AIS / 26AS / bank — uploaded vs required
│   │   ├── news-sync-status.tsx      # Background feed sync indicator (last poll, next)
│   │   └── toast-notifications.tsx   # Auto-dismiss progress feedback
│   ├── hooks/
│   │   ├── use-events.ts             # SSE event subscription
│   │   ├── use-progress.ts           # Real-time progress tracking
│   │   └── use-api.ts                # Fetch with retry, error handling
│   ├── lib/
│   │   └── api.ts                    # API client wrapper
│   ├── next.config.ts
│   └── package.json
├── docker-compose.yml                # Backend + news-worker + Ollama + DB
├── .github/workflows/
│   ├── ci.yml                        # Lint + unit tests on PR
│   └── integration.yml               # Integration tests on schedule
├── ollama_model.txt                  # Model to pull (e.g., mistral:7b or llama3.1)
└── README.md
```

---

## Phase 1: Foundation & Core Engine (Weeks 1-2)

**Goal**: Run the tax calculation engine without AI — get the math right for both jurisdictions.

### 1.1 Backend scaffolding
- FastAPI with `app/api/` routers mounted on `app/main.py`
- SQLite via SQLAlchemy with `db/models.py`
- Pydantic schemas in `app/schemas/`
- Event emitter/listener for internal process tracking
- **Structured logging from day one** (`app/core/logging.py`): JSON logs, request correlation IDs, tax-engine step traces — essential for debugging AI + calculation issues in later phases
- **Error handling conventions**: domain exceptions (`TaxRuleNotFound`, `UnsupportedFinancialYear`), global handler mapping to consistent API error shapes

### 1.1b India ↔ US comparative analysis (de-duplication)
Before implementing edge cases, maintain a **coverage matrix** mapping income types and treatments across jurisdictions:

| Concern | India | US | Shared engine? |
|---------|-------|-----|----------------|
| Salary | Slabs + 80C/HRA | Brackets + standard deduction | Separate slabs; shared `IncomeSource` model |
| Equity compensation | Perquisite / 17(2) | RSU ordinary income, 83(b) | Separate modules; shared vesting schedule parser |
| Capital gains | STCG/LTCG equity rules | 0/15/20% tiers | Separate rate tables; shared transaction schema |
| Foreign tax credit | Section 91 / DTAA | Form 1116 limitation | `dtaa.py` only — no duplicate FTC math |
| Filing artifacts | ITR-1/2 | 1040 + schedules | Separate report generators |

Use this matrix in code reviews to avoid duplicating logic (e.g., one capital-gains transaction model, two rate applicators) and to flag **gaps** (e.g., ESPP India vs US, advance tax vs estimated tax) early.

### 1.2 Data models (`db/models.py`)
```python
class User(Base):
    __tablename__ = "users"
    id: int
    display_name: str
    created_at: datetime

class Profile(Base):
    """Single active profile per user in v1; captures filing posture."""
    __tablename__ = "profiles"
    id: int
    user_id: int
    pan: str  # encrypted at rest
    residency_in: str  # "resident" | "nri" | "rnor"
    us_person: bool  # citizen/GC → worldwide US tax
    filing_status_us: str  # "single" | "mfj" | ...
    income_type_tags: list  # ["salary", "rsu", "interest"]

class TaxYear(Base):
    __tablename__ = "tax_years"
    id: int
    profile_id: int
    country: str  # "IN" | "US"
    financial_year: str  # "2025-26" | "2025"
    rule_version_id: str  # e.g. "IN_FY2024-25" — pinned at calculation time
    status: str  # "draft" | "filed" | "historical"
    source: str  # "manual" | "document"
    # Dual jurisdiction: same profile may have IN FY 2025-26 + US TY 2025; FTC links via dtaa.py

class IncomeSource(Base):
    __tablename__ = "income_sources"
    id: int
    tax_year_id: int
    type: str  # "salary" | "rsu" | "stock_options" | "equity_sale"
              # "fd_interest" | "mutual_fund" | "capital_gains"
              # "rental" | "business" | "other"
    amount_gross: Decimal
    amount_net: Decimal
    currency: str  # "USD" | "INR"
    exchange_rate: Decimal  # to INR at transaction date
    description: str
    document_id: int  # FK to Document

class Document(Base):
    __tablename__ = "documents"
    id: int
    profile_id: int
    filename: str
    file_path: str  # encrypted storage path
    mime_type: str
    document_type: str  # "form_16" | "ais" | ...
    type_confidence: float  # 0-1 from classifier
    financial_year: str  # detected FY, if applicable
    uploaded_at: datetime
    status: str  # "uploaded" | "parsing" | "parsed" | "error"
    extracted_data: JSON
    progress: int  # 0-100

class Deduction(Base):
    __tablename__ = "deductions"
    id: int
    tax_year_id: int
    type: str  # "80C" | "80D" | "standard_us" | ...
    amount: Decimal
    section: str
    document_id: int  # optional proof

class TaxCalculation(Base):
    __tablename__ = "tax_calculations"
    id: int
    tax_year_id: int
    rule_version_id: str  # copy of pack used — reproducible
    country: str
    regime: str  # "new" | "old" | "standard"
    gross_total: Decimal
    deductions_total: Decimal
    taxable_income: Decimal
    tax_before_credits: Decimal
    credits: Decimal  # HRA, LTA, FTC etc.
    tax_after_credits: Decimal
    surcharge: Decimal
    cess: Decimal
    final_tax: Decimal
    generated_at: datetime

class TaxNews(Base):
    __tablename__ = "tax_news"
    id: int
    source: str  # feed key, e.g. "in_notification_rss"
    feed_type: str  # "notification" | "circular" | "press_release" | "misc_comm" | "third_party_blog"
    source_type: str  # "official_government" | "regulatory_body" | "financial_media" | "tax_blogger"
    legal_authority: str  # "highest" | "high" | "medium" | "low" — drives RAG updater
    rag_priority: str  # "stage_statutory" | "stage_circular" | "stage_faq" | "alert_only"
    trust_score: float  # 0.0-1.0 — curated per feed, never LLM-determined
    title: str
    url: str
    pdf_urls: JSON  # extracted attachment links for rule PDFs
    guid: str  # RSS guid for deduplication
    published_at: datetime
    fetched_at: datetime
    raw_content: str
    classified_as: str  # "rate_change" | "section_amendment" | "new_exemption" | "deadline_change"
    relevance_score: float
    confidence_score: float
    linked_rules: list
    rag_processed: bool
    citations: JSON

class NewsSource(Base):
    """Curated feeds — never auto-discovered. Seeded at deploy from FEED_REGISTRY."""
    __tablename__ = "news_sources"
    id: int
    name: str
    feed_url: str  # full RSS URL
    feed_type: str  # notification | circular | press_release | misc_comm | third_party_blog
    source_type: str
    legal_authority: str
    rag_priority: str
    trust_score: float
    poll_interval_seconds: int  # default 300 (5 min) for official; 900 for third-party
    country: str  # "IN" | "US"
    last_successful_fetch: datetime
    last_error: str
    consecutive_failures: int
    active: bool

class RagIndex(Base):
    __tablename__ = "rag_index"
    id: int
    collection: str  # "statutory" | "circulars_faq" | "user_docs"
    rule_id: str
    text: str
    embedding_id: str
    metadata: JSON
    last_updated: datetime
    source: str
    staging: bool  # True until promoted from RSS/PDF pipeline

class ProcessEvent(Base):
    __tablename__ = "process_events"
    id: int
    profile_id: int
    process_type: str  # "document.parse" | "news.rag" | "calculation"
    event_name: str
    progress: int
    payload: JSON
    created_at: datetime

class SessionState(Base):
    __tablename__ = "session_state"
    id: int
    profile_id: int
    key: str  # "last_news_seen_id" | "last_open_at"
    value: str
    updated_at: datetime

class UserNewsPreference(Base):
    __tablename__ = "user_news_preferences"
    id: int
    profile_id: int
    category: str  # "rsu" | "80c" | "ftc"
    weight: float  # boost/penalty for relevance ranking
```

**RAG collections** (three Chroma collections — query order for Q&A):
1. **`statutory`** — Income Tax Act chunks, notification PDFs (promoted only)
2. **`circulars_faq`** — CBDT circulars, press releases, misc comms
3. **`user_docs`** — embedded extracts from uploaded Form-16, AIS, etc. (user-specific)

**Security (v1 local deployment)**:
- Encrypt uploads at rest (`file_path`); redact PAN/SSN in application logs
- Optional env `APP_PASSWORD` for single-user HTTP basic auth
- Never commit real documents; mocks only in repo

### 1.3 India tax engine (`tax_rules/india/`)

**New Regime (FY 2025-26)** — Finance Bill 2025:
- ₹0–₹3L: 0%
- ₹3L–₹7L: 5%
- ₹7L–₹12L: 10%
- ₹12L–₹15L: 15%
- Above ₹15L: 30%
- Standard deduction: ₹75,000 (₹1.25L for ≤60 yrs)
- Rebate u/s 87A: up to ₹60,000

**Old Regime** — slabs + Sections 80C–80U deductions
- 80C: ₹1.5L (PF, ELSS, life insurance, etc.)
- 80D: ₹25K–₹50K (health insurance)
- 80E: Unlimited (education loan interest)
- 80EEA: ₹1.5L (home loan)
- HRA exemption
- LTA exemption
- Standard deduction: ₹50,000

**Capital gains (equity)**:
- STCG (held ≤12 months): 15%
- LTCG (held >12 months): 10% on gains above ₹1.25L
- Debt fund LTCG: 20% with indexation (post-July 2024)

### 1.4 US tax engine (`tax_rules/us/`)

**Filing basics**:
- Standard deduction 2025: $14,600 single, $29,200 MFJ
- Income brackets (2025): 10%, 12%, 22%, 24%, 32%, 35%, 37%
- TCJA provisions expired → brackets adjust for inflation

**Capital gains 2025**:
- 0%/15%/20% based on income tier
- Short-term = ordinary income rate

**RSU taxation**:
- Vesting = ordinary income (W-2, box 16)
- Section 83(b) election window (30 days)
- Foreign employer = Form 1042-S, income from foreign source

**Foreign Tax Credit (Form 1116)**:
- India tax paid can offset US tax on same income
- Separate & general categories (salary, capital gains)
- Limitation = US tax × foreign source taxable income / total taxable income

**Forms — MVP vs later**:
| Output | v1 | v1.1+ |
|--------|----|-------|
| Tax calculation breakdown (PDF/JSON) | Yes | — |
| Regime comparison report | Yes | — |
| ITR-1 / ITR-2 PDF or XML | No | Yes |
| Form 1040 + schedules (8949, 1116) | No | Yes |
| FBAR (FinCEN 114) / Form 8938 | No | Yes (wizard + thresholds) |

### 1.5 Testing strategy (applies across all phases)

**Unit Tests (70% of test suite)**:
- Tax engine: every slab boundary, edge case, exemption, cap
  - `test_new_regime_slab_boundaries`: exact boundary values (299999, 300000, 300001, etc.)
  - `test_old_regime_hra`: basic*40%, basic*50%, rent-10%, actual HRA — minimum wins
  - `test_capital_gains_ltcg_exemption`: ₹1.25L exemption, different holding periods
  - `test_ftc_limitation_formula`: general category, separate category, carryforward
  - `test_rsu_vesting_schedule`: pro-rata vesting, partial exercises
  - `test_india_surcharge_cess`: progressive surcharge + 4% cess
- News fetchers: mock responses, parse correctness
- RAG chunking: verify chunk size, overlap, retrieval order
- Document parser: prompt output validation against schema
- Rule-change regression: labeled RSS items → expected `rag_priority` + whether `rule_versions` must bump

**Integration Tests**:
- Full calculation flow: income entry → run calculation → verify output
- Document pipeline: upload → parse → extract → validate → save
- RAG update: fetch → chunk → embed → retrieve → verify relevance
- RSU full flow: vest → sell → calculate India tax + US tax + FTC → compare
- News pipeline: fetch → parse → classify → store → notify
- SSE event flow: event emitted → listener receives → UI updated

**Test infrastructure**:
- `tests/conftest.py` shared fixtures: in-memory DB, tax year factory, income factory, mock LLM
- `pytest-asyncio` for async tests
- `httpx.AsyncClient` for API testing
- Tax engine assertions against known-good calculators (ClearTax, IRS interactive tools)
- Coverage target: 95%+ for tax engine, 80%+ for API

### 1.6 Prior-year tax calculation (versioned rules)

**Use case**: User uploads a **previous** Form-16 (e.g. FY 2023-24), W-2 (TY 2023), or filed ITR/1040 → system extracts income and runs the engine using **that year's** slabs, deductions, and limits — not the current FY defaults.

**Rule versioning** (`tax_rules/rule_versions.py`):
- Each supported FY/TY is a discrete rule pack: slab tables, standard deduction amounts, rebate limits, US bracket inflation
- `TaxCalculation` stores `rule_version_id` so results are reproducible even if current-year rules change later
- Initial packs: current FY + prior 2 FYs (expandable); API returns `422` with clear message if FY unsupported

**Flow**:
```
Upload Form-16 (FY 2023-24) → parser extracts financial_year + line items
  → Create TaxYear(country=IN, financial_year="2023-24", status=historical, source=document)
  → Resolve rule pack IN_FY2023-24 → run india engine (old/new regime if applicable for that year)
  → Optional: compare to TDS / tax_deducted on Form-16 ("computed ₹X vs TDS ₹Y")
```

**API**:
```
POST   /api/calculation/run?tax_year_id=...   # Uses TaxYear.financial_year → rule pack
POST   /api/tax-years/from-document/{doc_id}  # Auto-create TaxYear from parsed FY
GET    /api/tax-years/compare?base=...&prior=...  # YoY liability / effective rate
```

**Tests**: `test_prior_year.py` — known Form-16 fixtures per FY against ClearTax/IRS snapshots for that year.

### 1.7 Rule-change workflow (code vs RAG — must not drift)

Legislative notifications can change **Q&A text** and **calculation numbers**. Keep them aligned:

```
RSS notification ingested
  → classify + map to rule_id(s)
  → IF affects slabs/rates/rebate (rule_versions manifest):
        update rule_versions.py pack + pytest golden → blocking CI
     ELSE:
        staging RAG only (statutory / circulars_faq)
  → human promote staging → production collections (Settings UI)
  → never auto-delete production chunks without promote + regression pass
```

- **Calculation** always reads `rule_versions.py` + `TaxYear.rule_version_id` — never raw RAG for numeric tax.
- **Q&A** reads RAG collections; cites `rule_version_id` and last-promoted timestamp.
- Optimizer suggestions are validated by re-running the deterministic engine before display.

### 1.8 TurboTax-style mock & fixture requirements (mandatory for dev/CI)

**Goal**: Every user journey runs without real documents or live LLM — same pattern as TurboTax engineering fixtures (scenario → documents → expected line items → expected tax).

**`backend/mocks/scenarios/`** — named profiles:
```json
{
  "id": "salaried_india_new_regime",
  "display_name": "Salaried — India new regime FY 2025-26",
  "residency": "resident",
  "countries": ["IN"],
  "income_types": ["salary"],
  "documents_required": ["form_16", "ais", "form_26as", "bank_savings_interest"],
  "expected_final_tax_inr": 187200,
  "tolerance_inr": 100
}
```

**`backend/mocks/documents/`** — synthetic files per type (PDF/CSV generated in-repo, no PII):
- Form-16, payslips, 26AS, **AIS export (JSON/PDF)**, bank interest certificate, brokerage, RSU grant

**`backend/mocks/golden/`** — expected `TaxCalculation` JSON per scenario + regime

**`backend/mocks/llm/`** — recorded parser/Q&A outputs; `USE_MOCK_LLM=1` in CI

**`backend/mocks/rss/`** — frozen XML from each official feed for `test_rss_parser.py`

**`backend/mocks/feed_registry.json`** — seeds `NewsSource` at deploy (all India RSS URLs + Taxmann/TaxGuru + `feed_type`, `rag_priority`, `poll_interval_seconds`).

**Demo / dev mode**:
```
POST /api/dev/load-scenario/{scenario_id}  # Seeds DB from fixture (dev only)
GET  /api/dev/scenarios                    # List available mocks
```

**Frontend mock mode**: `NEXT_PUBLIC_USE_MOCK_API=true` serves MSW handlers mirroring OpenAPI for UI work without backend.

**Interview checkpoints** (TurboTax-style wizard state stored per scenario):
- Residency confirmed → documents checklist → income reviewed → calculation → optimization

---

## Phase 2: Document Ingestion & AI Parsing (Weeks 3-4)

**Goal**: Upload documents → extract structured data via LangChain + Ollama.

### 2.1 Document upload endpoints
```
POST   /api/docs/upload       # Upload PDF/CSV/Excel
GET    /api/docs               # List all documents
GET    /api/docs/{id}          # Document detail + extracted data
DELETE /api/docs/{id}          # Delete document
```

### 2.2 LangChain pipeline
```python
# app/ai/document_parser.py
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Document types with structured extraction prompts:
DOCUMENT_EXTRACTORS = {
    "salary_slip": {
        "schema": {"employer": str, "month": str, "basic": float, "hra": float,
                    "special_allowance": float, "ta": float, "pf": float,
                    "tax_deducted": float, "gross": float, "net": float},
        "prompt": "Extract salary details from this payslip..."
    },
    "form_16": {
        "schema": {"employer": str, "pan": str, "financial_year": str,
                    "salary_gross": float, "investments_declared": float,
                    "tax_deducted": float, "chapter_v_section": str},
        "prompt": "Extract Form 16 details..."
    },
    "brokerage_statement": {
        "schema": [{"symbol": str, "asset_type": str, "qty": float,
       "purchase_price": float, "sale_price": float, "purchase_date": str,
       "sale_date": str, "exchange": str}],
        "prompt": "Extract equity transactions from brokerage statement..."
    },
    "rsu_award": {
        "schema": {"employer": str, "total_grants": int, "vesting_schedule": [...],
       "shares_vested": int, "vest_price": float, "vest_date": str,
       "us_tax_withheld": float, "india_tax_withheld": float},
        "prompt": "Extract RSU grant details..."
    },
    "form_26as": {
        "schema": [{"transaction_date": str, "description": str, "amount": float,
       "tax_deducted": float, "deductor": str}],
        "prompt": "Extract TDS entries from Form 26AS..."
    },
    "ais": {
        "schema": {
            "financial_year": str,
            "pan": str,
            "part_a_tds": [{"deductor": str, "section": str, "amount": float, "tax_deducted": float}],
            "part_b_sft": [{"type": str, "description": str, "amount": float}],  # high-value transactions
            "part_c_tax_payments": [{"type": str, "amount": float, "date": str}],
            "part_d_other": [{"category": str, "amount": float, "description": str}]  # interest, dividends, etc.
        },
        "prompt": "Extract Annual Information Statement (AIS) from ITD export JSON or PDF..."
    },
    "bank_savings_interest": {
        "schema": {"bank_name": str, "account_last4": str, "financial_year": str,
                    "interest_credited": float, "tds_deducted": float, "form_15g_filed": bool},
        "prompt": "Extract savings account interest certificate (Form 16A style or bank statement)..."
    },
    "bank_fd_interest": {
        "schema": {"bank_name": str, "fd_account": str, "interest": float, "tds": float, "financial_year": str},
        "prompt": "Extract FD interest certificate..."
    },
    "form_1099": {
        "schema": {"form_type": str, "boxes": {"1": float, "4": float, "14": float}},
        "prompt": "Extract Form 1099 details..."
    },
    "espp_statement": {
        "schema": {"employer": str, "plan_name": str, "purchase_price": float,
                    "fair_market_value": float, "purchase_date": str,
                    "qualifying_disposition": bool, "contribution_total": float,
                    "shares_purchased": int, "discount_pct": float},
        "prompt": "Extract ESPP (Employee Stock Purchase Plan) details from statement..."
    },
    "stock_award": {
        "schema": {"employer": str, "award_type": str,  # "RSU" | "NSO" | "ISO"
                    "grant_date": str, "exercise_price": float, "shares_granted": int,
                    "shares_vested": int, "vesting_schedule": [...],
                    "fmv_on_grant": float, "fmv_on_vest": float},
        "prompt": "Extract equity award details (RSU/NSO/ISO) including vesting schedule, FMV, and grant terms...""
    },
    "w2_form": {
        "schema": {"employer_ein": str, "employee_ssn": str,
                    "boxes": {"1_wages": float, "3_social_wages": float,
                              "4_social_tax": float, "5_medicare_wages": float,
                              "6_medicare_tax": float, "14_state": float,
                              "15_state_name": str, "16_state_wages": float,
                              "17_state_tax": float, "1_fed_tax_withheld": float}},
        "prompt": Extract W2 form details including all box entries..."
    },
}
```

**AIS parsing order**: Prefer **ITD JSON export** (`json.loads` + Pydantic schema) — no LLM. Use LLM/OCR only for AIS PDF or scanned Form-16. Support password-protected PDFs via upload-time password field.

**OCR**: Tesseract or `pdf2image` + Ollama vision fallback for scanned payslips; flag `low_ocr_confidence` on `Document`.

### 2.3 Parsing flow (with full visibility)
```
User uploads PDF → Event: document.uploaded (progress: 0%)
  → Event: parsing.started (progress: 10%)
  → PDF text extraction → Event: parsing.text_extracted (progress: 30%)
  → LLM extraction → Event: parsing.llm_complete (progress: 70%)
  → Validation → Event: parsing.validating (progress: 85%)
  → Save to DB → Event: parsing.complete (progress: 100%)
  → Event: parsing.ready_for_review (user notified)
```

Every step emits an SSE event + stores in `process_events` table. Frontend `pipeline-tracker.tsx` shows real-time progress bars.

### 2.4 Parsing fallbacks & validation (beyond LLM output)

**When LLM parsing fails or confidence is low**:
- **Manual override UI**: editable extraction table on document detail page; user corrections saved to `extracted_data` with `source: "manual"`
- **Re-parse** with alternate prompt or smaller chunk strategy
- **Template fallback**: regex/heuristic extractors for Form-16 Part B, W-2 boxes, 26AS TDS rows (no LLM) when PDF text is structured
- **Partial success**: save high-confidence fields, flag low-confidence fields for review

**Validation layers** (post-parsing, pre-commit):
1. JSON schema validation (Pydantic) against per-doc-type schema
2. **Cross-field checks**: gross ≥ net; TDS ≤ gross; FY on Form-16 matches user-selected or auto-detected year
3. **Cross-document reconciliation**: Form-16 salary vs payslips; **AIS Part-A TDS vs 26AS**; **AIS interest vs bank certificate**; Form-16 Part A TDS vs 26AS
4. **Sanity bounds**: amounts within configurable min/max per field type
5. **Prior-year routing**: if `financial_year` ≠ active filing year → attach to `TaxYear(status=historical)` and surface "Calculate for FY 2023-24" CTA

### 2.5 Ollama setup
```dockerfile
# docker-compose.yml service
ollama:
  image: ollama/ollama
  ports: ["11434:11434"]
  volumes: ["ollama_data:/root/.ollama"]
```

Suggested models:
- Document parsing: `llama3.1:8b` or `qwen2.5:14b`
- RAG staging diff / section mapping (notifications): `qwen2.5:14b` minimum; `qwen3.5:35b` if GPU ≥ 24GB VRAM

**Hardware**: Document + Q&A fit 8–16GB VRAM. Staging diff for notifications on 35B needs **≥24GB** or run via smaller model + mandatory human promote. CI uses `USE_MOCK_LLM=1` only.

---

## Phase 3: News Monitoring & RAG Management (Weeks 5-6)

**Goal**: Tax rules and articles stay current **automatically** while the system is up and online — not only when the user opens the news page.

### 3.1 Continuous background news worker (always-on)

**Behavior**:
- Starts with FastAPI lifespan (or separate `news-worker` container in docker-compose)
- **While process is running AND `internet_available()`**: outer loop every `news_poll_tick_seconds` (default **60s**); each feed polled only when `now - last_successful_fetch >= poll_interval_seconds` (default **300s** official, **900s** third-party)
- On network loss: pause polls, emit `news.sync_paused`; resume with backoff when connectivity returns
- On app/UI open: **no extra fetch required** — UI reads latest from DB; optional `GET /api/news/sync-status` shows last poll time
- Deduplicate by RSS `guid` + normalized URL hash
- Emit SSE: `news.item.ingested`, `news.rag.updated`, `news.sync.error`

```python
# app/news/background_worker.py (simplified)
async def run_forever():
    while True:
        if not network_up():
            await asyncio.sleep(60)
            continue
        for source in NewsSource.filter(active=True).order_by("legal_authority"):
            await fetch_and_process(source)
        await asyncio.sleep(settings.news_poll_tick_seconds)  # default 60s between full cycles
```

**On-open fetch** (supplemental only): if user was offline for days, one catch-up pass on news page load for items since `last_seen_article_id` — does not replace background worker.

### 3.1a Official India RSS feeds (primary — Income Tax Department)

Subscribe via `feedparser` + custom `rss_parser.py` (extract title, link, pubDate, `guid`, HTML description, **PDF download links** from item body/enclosures).

| Feed key | URL | Why it matters |
|----------|-----|----------------|
| `in_notification` | `https://www.incometaxindia.gov.in/notification-rss-feed/-/asset_publisher/bxhj/rss` | New legislation, ITR structural changes, Section 115BAC etc. — **drives code/rule changes** |
| `in_circular` | `https://www.incometaxindia.gov.in/circular-rss-feed/-/asset_publisher/bxhj/rss` | CBDT clarifications, deadline extensions — **execution context for Q&A** |
| `in_press_release` | `https://www.incometaxindia.gov.in/press-release-rss-feed/-/asset_publisher/bxhj/rss` | Compliance initiatives, plain-English summaries — **FAQ / contextual answers** |
| `in_misc_comm` | `https://www.incometaxindia.gov.in/miscellaneous-communications-rss-feed` | Smaller admin updates not in formal circulars |

Reference: [Subscribe to Tax Feeds — Income Tax Department](https://www.incometaxindia.gov.in/Pages/tax-feeds.aspx)

**`rss_parser.py` responsibilities**:
```python
def parse_feed(xml: str) -> list[FeedItem]:
    """Return normalized items with pdf_urls[], guid, published_at, raw_html."""

def extract_pdf_links(item_html: str, item_link: str) -> list[str]:
    """Follow item page if needed; collect .pdf hrefs for ingestion pipeline."""
```

### 3.1b Third-party fallback feeds (cross-verify, never primary law)

| Feed key | URL | Role |
|----------|-----|------|
| `taxmann_statutory` | `https://www.taxmann.com/rss/statutory-happening.ashx` | Statutory amendments + court rulings — **trigger re-scrape if gov feed silent >24h** |
| `taxguru_daily` | `http://feeds.feedburner.com/taxguru/cwwk` | Fast amendment alerts — **backup alert only**; do not replace gov notification chunks |

Optional: `https://www.taxmann.com/rss/news.ashx` for headline corroboration (low RAG priority).

**Gov downtime handling**:
- If all 4 official feeds fail `consecutive_failures >= 3`: raise dashboard alert; increase Taxmann poll frequency
- When official feeds recover: run diff merge — third-party-only items flagged `needs_official_confirmation`

### 3.1c Feed priority → RAG updater logic (`feed_priority.py`)

| Feed type | Legal authority | `rag_priority` | Vector DB action |
|-----------|-----------------|----------------|------------------|
| **Notifications** | Highest (changes law) | `stage_statutory` | Write to **staging** `statutory` collection; flag if `rule_versions` manifest needs bump; **promote** via Settings after review + pytest |
| **Circulars** | High (clarifies execution) | `stage_circular` | Staging `circulars_faq` linked to `rule_id` |
| **Press releases** | Medium (public guidance) | `stage_faq` | Staging `circulars_faq` only |
| **Misc communications** | Medium-low | `stage_faq` | Same as press releases |
| **Third-party blogs** | Low (commentary) | `alert_only` | UI alert only; corroboration boost if gov item exists |

```python
RAG_ACTIONS = {
    "stage_statutory": lambda item: staging.write(collection="statutory", item=item),
    "stage_circular": lambda item: staging.write(collection="circulars_faq", item=item),
    "stage_faq": lambda item: staging.write(collection="circulars_faq", item=item),
    "alert_only": lambda item: news_store.save_alert(item),
}
# POST /api/rag/promote — copies staging → production; snapshots previous production for rollback
```

**Processing pipeline per new item**:
```
RSS poll → parse XML → dedupe by guid → classify (LLM) → RAG_ACTION → staging embed
  → if pdf_urls: download → pdfplumber → chunk
  → if rule_versions manifest hit: open PR / task to bump Python rule pack + golden tests
  → emit news.staging.ready → UI badge ("N items awaiting promote")
```

- **Classification** (LLM): `rate_change` | `section_amendment` | `new_exemption` | `deadline_change` | `no_impact`
- **Relevance scoring**: 0–1 vs user profile (RSU, 80C, NRI, etc.)
- **Alerts**: UI toast for `stage_statutory` pending promote or high-relevance circulars

### 3.1e US / IRS feeds (v1.1 — stub in v1)

v1 ships **India RSS automation** only. `irs.gov.py` is a stub with manual PDF upload to RAG. v1.1 adds IRS RSS (e.g. newsroom / IRB) using the same `feed_priority` pattern and `US_TYxxxx` rule packs.

### 3.1f Trust scores & user feedback loops

**Dynamic trust adjustment** (curated sources only — never LLM-assigned base trust):
- Admin can bump/demote `NewsSource.trust_score` when reliability changes
- **Decay/recovery rules**: optional time-based decay for financial_media if not re-verified in N days
- **Corroboration boost**: when 2+ official sources report same change, raise `confidence_score` on the merged card (not base trust)

**User feedback on relevance** (`POST /api/feedback/news`):
```json
{ "news_id": 42, "rating": "relevant" | "not_relevant" | "incorrect", "comment": "..." }
```
- Per-user relevance adjustments stored in `UserNewsPreference` (boost/penalize categories: RSU, 80C, FTC)
- Feed ranking: `trust_score` (global) → personalized relevance → date
- Feedback exported for periodic review of classification prompts

### 3.2 RAG management

See **§3.3** for endpoint list. Manual PDF scrape (§3.2b) also writes to **staging** first.

**RAG update flow** (with full visibility):
```
User triggers "Update Tax Rules" → Event: rag_update.started
  → Fetch official sources → Event: rag_update.fetched (sources: X/Y)
  → Load new/changed rules → Event: rag_update.rules_loaded (rules: X new, Y changed)
  → Chunk rules → Event: rag_update.chunked (chunks: X)
  → Generate embeddings → Event: rag_update.embedded (progress: X%)
  → Write staging → Event: rag_update.staged (chunks: X)
  → User promotes → Event: rag_update.promoted
  → User notified: "3 chunks promoted; 1 rule pack bump required for calculation"
```

**RAG storage**: ChromaDB persistent; three production collections + one `staging` collection per type. Metadata: `source`, `effective_date`, `rule_id`, `news_item_id`.

**Promote flow** (Settings → RAG):
```
View staging diff (N new, M updated chunks) → Run retrieval smoke tests
  → POST /api/rag/promote → copy to production → snapshot for rollback
```

### 3.2b India Tax Rules PDF Ingestion

Source: `https://www.incometaxindia.gov.in/income-tax-rules`

- **PDF discovery**: Scrape the page for all links to PDF documents (circulars, notifications, rules, amendments). Each PDF URL is cataloged with metadata: title, publish_date, document_type, file_size, and last_modified.
- **Download & storage**: All PDFs are downloaded to a dedicated local directory (e.g., `data/tax-rules-pdfs/`) organized by year and document type. New or updated PDFs are detected by comparing file size, last_modified header, or a hash stored in a local `tax_rules_catalog` table. On each run, only delta updates (new + changed) are downloaded.
- **Ingestion pipeline** (runs on schedule + on manual trigger):
  ```
  Scrape page for PDF links → Download new/changed PDFs → Parse with pdfplumber →
  Chunk text (by section/headings for legal structure) → Embed with Ollama →
  Store in ChromaDB with metadata (section_no, amendment_date, document_type)
  ```
- **Change detection**: Before re-ingesting, check if a PDF has been updated (ETag / last-modified header / file hash). Only re-process changed files to save compute.
- **Storage layout**:
  ```
  data/tax-rules-pdfs/
    ├── 2026/
    │   ├── notifications/
    │   ├── circulars/
    │   └── amendments/
    └── 2025/
        ├── notifications/
        └── circulars/
  ```
- **RAG usage**: Q&A queries `statutory` → `circulars_faq` → `user_docs` (see §1.2). Income classification uses engine + user_docs, not news items.

### 3.3 API endpoints

**Phase 1 — calculation & tax years** (also listed in §1.6):
```
POST   /api/calculation/run
GET    /api/calculation/{id}
POST   /api/tax-years/from-document/{doc_id}
GET    /api/tax-years/compare
```

**Phase 3 — news & RAG**:
```
GET    /api/news/feed                    # ?trust=official|feed_type=notification&country=IN
GET    /api/news/sync-status
GET    /api/news/feeds
POST   /api/news/poll-now
GET    /api/news/{id}
GET    /api/news/alerts
POST   /api/news/on-open-fetch
POST   /api/rag/status
POST   /api/rag/update
GET    /api/rag/rules                   # List production chunks (metadata)
GET    /api/rag/staging                 # Pending chunks awaiting promote
POST   /api/rag/promote
DELETE /api/rag/reset
```

**Phase 4 — agents**:
```
POST   /api/optimization/run
GET    /api/optimization/{id}
POST   /api/qa/chat
POST   /api/reports/generate             # Summary PDF/JSON (v1)
```

**Cross-cutting**:
```
POST   /api/events/stream
POST   /api/feedback/{area}
```

### 3.4 Pay-slip deduction explanation API
```
POST   /api/pay-slip/explain              # Explain all deductions in a payslip
GET    /api/pay-slip/explain/{pay_slip_id} # Get explanation for uploaded payslip
GET    /api/pay-slip/deductions/{line_id}  # Get legal proof for a specific deduction line
```

**Deduction explanation structure** (each deduction line returns):
```json
{
  "line_name": "TDS",
  "amount": 25000,
  "formula": "Taxable income = ₹12,00,000. Tax = ₹1,87,200 (after 80C) × slab rate. TDS = ₹25,000/month",
  "legal_basis": "Income Tax Act, 1961 — Section 192 (Salary Tax)",
  "citation": "https://www.cbdt.gov.in/tech/IT Act 1961 -Ch 3.pdf#page=89",
  "proof_documents": ["Form 16 Part A (Q4)", "RSU Vesting Statement - 100 shares @ $85"],
  "proof_lines": [{"doc": "RSU Vesting Statement", "line": "Tax withholding: $850 × 100 shares"},
                  {"doc": "Form 16", "line": "Box 16: TDS ₹3,00,000 (annual)"}],
  "eligibility": "Applicable because salary exceeds ₹2.5L threshold",
  "summary": "₹25,000 deducted monthly for income tax. Annual total: ₹3,00,000."
}
```

### 3.5 Tax forecasting API
```
POST   /api/forecast/projection          # Generate full-year forecast based on current data
POST   /api/forecast/whatif              # Simulate what-if scenarios
GET    /api/forecast/summary             # YTD + projected totals
```

**What-if slider parameters**:
```json
{
  "slider_type": "80c_investment",
  "current_value": 100000,
  "new_value": 150000,
  "tax_year": 2025
}
```

**Forecast output**:
```json
{
  "ytd_income": 750000,
  "ytd_tax_paid": 85000,
  "projected_annual_income": 1200000,
  "projected_annual_tax": 165000,
  "effective_rate": "13.75%",
  "monthly_in_hand": [65000, 65000, 72000, 72000, 68000, 135000],
  "deadline_alerts": [
    {"type": "80c_investment", "message": "Invest ₹50,000 more in 80C before March 31"},
    {"type": "advance_tax", "message": "Pay ₹15,000 advance tax by June 15 (Q2 deadline)"}
  ]
}
```

---

## Phase 4: AI Agents & Interactive Q&A (Weeks 7-8)

**Goal**: Conversational interface for tax questions and optimization.

### 4.1 Agent architecture

**Optimizer rule**: Every optimization suggestion must be re-run through `tax_rules/optimizer.py` + full calculation; discard if engine result does not improve tax or violates caps.

```python
# Parsing agent: extracts data from documents (Phase 2)
# Calculation agent: runs tax engine + explains results
# QA agent: answers general tax questions with RAG over tax code (always cites sources)
# Optimizer agent: suggests tax-saving strategies based on user's full profile
# PayExplainer agent: analyzes payslip deductions and produces line-by-line breakdown with proof
# DocRequester agent: AIS/26AS/bank checklist + missing doc prompts (Phase 2 doc types)
# TaxForecaster agent: projects full-year tax based on YTD + AIS + what-if scenarios
#
# RAG sources (staging → promote via background RSS + manual PDF scrape):
# - statutory: Income Tax Act + notification PDFs
# - circulars_faq: CBDT circulars, press releases
# - user_docs: uploaded Form-16, AIS, etc.
# - US IRC 1, 861-862, 911-912, 956-964, 1042, 1116; DTAA; case law
```

### 4.2 Q&A agent design
- Retrieves in order: `statutory` → `circulars_faq` → `user_docs` (see §1.2)
- Citations included (source URL, section number, date, `rule_version_id`)
- Shows last RAG promote timestamp in UI
- If no relevant docs, says so — never invent rates; numeric answers must match engine when calculation exists

### 4.3 Agent-driven doc request (incl. AIS & bank statements)

**Required document checklist** (India salaried baseline — agent enforces before "ready to file"):
| Document | Purpose |
|----------|---------|
| **AIS** (Annual Information Statement) | Authoritative view of TDS, SFT, interest, dividends — reconciles with 26AS |
| **Form 26AS** | TDS credit verification |
| **Form 16** | Salary + employer TDS |
| **Bank savings interest certificate** | Section 80TTA/TTB, interest income, TDS on interest |
| Bank FD / other interest certs | If AIS shows FD or other interest |
| 80C/80D proofs | If claiming deductions beyond Form-16 declarations |

- **Missing doc detection** examples:
  - "AIS is not uploaded — I cannot reconcile ₹42,000 interest shown in Form-16 with ITD records"
  - "AIS Part B shows a high-value equity sale but no 1099-B / brokerage statement uploaded"
  - "Bank savings interest certificate missing — AIS reports ₹8,200 interest from HDFC"
  - "I can see ₹50K deducted but need your ESPP statement to explain the breakdown"
- **Smart doc suggestions**:
  - "Download AIS from incometax.gov.in → AIS → Download JSON/PDF → upload here"
  - "Upload bank interest certificate (Apr–Mar) for each bank AIS lists"
  - "Upload 80C proofs → I can calculate your full deduction"
- **Doc availability tracking**: `documents-checklist.tsx` — required vs optional vs uploaded, with ITD portal links
- **"Explain this deduction" flow**: hover payslip line → agent names proof doc (AIS line, 26AS, bank cert)

### 4.4 PayExplainer agent
- When a payslip is uploaded, this agent analyzes every deduction line
- Matches each deduction to: (1) applicable law, (2) user's document proof, (3) calculation formula
- Handles special cases: ESPP discount tax, RSU withholding, stock grant tax, Section 17(2) employer contribution
- Cross-references with uploaded 1099-B, grant letters, ESPP confirmations to produce proof
- If a deduction has no matching document, flags it: "₹25,000 ESPP deduction found — need ESPP statement to explain"

### 4.5 TaxForecaster agent
- Builds YTD model from pay slips + 1099s + **26AS + AIS** + bank interest certs
- Projects full-year income, deductions, effective tax rate
- Simulates what-if scenarios: bonus, investment change, stock vesting timing, regime change
- Produces deadline alerts: advance tax, 80C deadline, estimated tax payment due dates

### 4.6 Agent coordination & load management

**Avoid bottlenecks**:
- **Orchestrator** routes work: parsing and calculation are independent; Q&A does not block uploads
- **Parallel where safe**: multi-document parse jobs run concurrently (semaphore-limited)
- **Prioritization**: user-initiated calculation > document parse > Q&A > background news poll > RAG embed jobs

**Request queue** (Redis or in-process for MVP):
- Agent endpoints (`/api/qa/chat`, `/api/optimization/run`, heavy parse) enqueue when Ollama concurrency exceeded
- SSE progress includes `queue_position` and estimated wait
- Configurable max concurrent LLM calls (default 2 on local Ollama)

---

## Phase 5: Frontend UI (Weeks 9-12)

**Goal**: User-friendly, fully transparent UI with real-time process visibility.

### 5.0 UX quality (plan review)

- **User testing checkpoints** (before Phase 6 lock): 3–5 task-based sessions (upload Form-16, confirm extraction, run prior-year calc, read news card, ask one Q&A question); capture friction in issue tracker
- **First-time user aids**: guided tour on dashboard (tax year, residency, upload); contextual tooltips on regime selector, trust badges, and "Why this number?"
- **Accessibility**: keyboard-navigable forms, sufficient contrast on trust badges

### 5.1 Dashboard
- **Income summary card** — total income by source, by jurisdiction, by year
- **Tax liability card** — current year liability, **comparison with prior year** (when historical `TaxYear` exists from prior Form-16 / ITR)
- **Tax year switcher** — toggle active filing year vs historical years computed from uploaded docs
- **Regime selector** — one-click old vs new comparison
- **News alerts panel** — top 5 relevant rule changes
- **Recent activity feed** — last uploads, calculations, document parses
- **Status badges** — "Tax year 2025-26: 3 documents pending review"

### 5.2 Document management page
- **Drag-and-drop upload** with progress bars
- **Document cards** showing: name, type, status (uploaded/parsing/parsed/error), progress %, extracted data preview, **detected financial year** (e.g. "FY 2023-24 from Form-16")
- **Confirmation step** — extracted data shown as editable table before committing to income sources (**manual override** when LLM wrong)
- **Re-parse** button for documents that were parsed incorrectly
- **"Calculate tax for this year"** — one-click from parsed prior-year Form-16 → historical `TaxYear` + calculation run
- **Filter by status** — pending review, confirmed, errored

### 5.3 Income entry page
- **Multi-step form** with progress indicator
- **Autofill from documents** — "We found 12 items from your uploaded Form 16"
- **Validation** — inline field validation with helpful messages
- **Autosave** — draft saved every 30 seconds
- **Bulk import** — CSV template download + upload
- **Currency handling** — auto-conversion with rate display
- **Linked pay-slip timeline** — after uploading pay slips, YTD totals auto-computed
  and displayed alongside manual entry to cross-check

### 5.4 Tax calculation page
- **Regime comparison table** — side-by-side old vs new with line-by-line breakdown
- **Visual breakdown** — bar/area charts showing income by source, tax by component
- **Slab visualization** — income filling up tax slabs visually
- **Tax by component** — income tax, surcharge, cess, credits, net tax
- **Line-by-line detail** — expandable rows with explanation for each number
- **"Why this number?"** — hover tooltips citing relevant sections

### 5.5 Payslip deduction explainer page
- **Upload a payslip** (or multiple monthly payslips) → AI extracts every deduction line item
- **Line-by-line explanation** for each deduction — with *proof and legal basis*:
  - **Standard deductions** — PF, ESI, Professional Tax, TDS:
    - "PF ₹1,728 = 12% of Basic. *Proof: [EPFO Notification](url) — mandatory for establishments with 20+ employees*"
  - **ESPP-related** — if ESPP purchase is deducted:
    - "ESPP ₹12,000 = 100 shares × ($50 FMV - $40 purchase price). *Proof: [ESPP Statement](url) — Section 421A applies if Indian subsidiary, FTB Notice 2022-38 for CA apportionment*"
  - **Stock grant vesting** — RSU/stock grant withholding:
    - "TDS ₹8,500 on RSU vest = 100 shares × $85 FMV × 30% (highest marginal + surcharge). *Proof: Your grant letter vesting schedule shows 100 RSUs vesting on [date]*"
  - **Additional tax** — due to multiple income sources / slab jump:
    - "Surcharge ₹2,100 = income crossed ₹50L threshold → 25% becomes 30%. *Proof: Section 2(29A) of Finance Act + surcharge clause*"
  - **Each line shows**: amount, formula, what it maps to in your docs, legal citation, and a "View proof" link to your uploaded document
- **Deduction categories** — grouped tabs: "Standard (PF/TDS)", "Equity (ESPP/RSU)", "Investments (80C/HRA)", "Other"
- **Month-over-month** — if 12 months uploaded, show which months had equity deductions vs. standard
- **Exportable summary** — "Show me all equity-related income for Form 26AS reconciliation"

### 5.6 Tax forecasting page
- **YTD projection** — based on current month's pay, project full-year income, deductions, tax
- **What-if sliders**:
  - "What if I increase 80C investment by ₹X?"
  - "What if I get a bonus of ₹Y in March?"
  - "What if my stock vests at $X instead of $Y?"
  - "What if I change my ESPP contribution?"
- **Forecast chart** — month-by-month visual of in-hand pay, cumulative tax, effective tax rate
- **Deadline reminders** — "Invest ₹50K more in 80C before March 31"
- **Quarterly tax planner** — "You need to pay ₹X more as advance tax by June 15"

### 5.7 Document uploader (RAG training)
- **Drag-and-drop + file picker** for all financial documents, grouped by category:
  - **Salary**: Payslips (monthly), Form 16, Form 16A, appointment letter, hike letters
  - **Equity**: RSU/NSO/ISO grant letters, vesting schedules, ESPP statements, 1099-B (brokerage), 1042-S (foreign contractor)
  - **Income**: W2, 1099-MISC/NEC, 1099-DIV, 1099-INT, K-1, bank interest certificates
  - **Investments**: 80C proofs (PPF, ELSS, FD, LIC), 80D (health insurance), HRA, LTA
  - **ITD compliance (required for India filing)**: **AIS** (JSON/PDF export), Form 26AS, TDS certificates
  - **Banking**: Savings interest certificates, FD interest certs, bank statements (if no formal cert)
  - **Other**: Prior year ITR, capital gains statements
- **Auto-type detection** — AI identifies document type and extracts relevant data automatically
- **Validation** — "We found 4 pay slips for Jan-Apr. March is missing. Also, your RSU vesting statement from June is not uploaded."
- **RAG ingestion** — extracted data + source documents indexed for RAG so QA agent can reference your specific financial situation
- **Smart upload suggestions** — agent suggests what to upload: "To explain your ₹50K deduction, upload your ESPP confirmation"

### 5.8 News page — citation-first, trust-first design
- **News cards** with prominent trust indicators:
  - **Trust badge** — color-coded pill: `🏛️ Official` (0.9-1.0), `📋 Regulatory` (0.7-0.9), `📰 Financial Media` (0.5-0.7), `⚠️ Unverified` (<0.5)
  - **Source label** — full source name, not short codes: "CBDT Notification", "IRS Revenue Procedure", not "cbdt" / "irs"
  - **Direct citation link** — clickable URL that opens the official government/media page in a new tab (the *source of truth*)
  - **Citation block** — auto-extracted citations like "Finance Bill 2025, Clause 12(3)" or "IRC Section 961(a)" shown as inline badges
  - **Cross-source confidence** — if 2+ authoritative sources report the same change, show "✓ Corroborated by [IRS] + [Treasury]" with a higher confidence score
  - **Published date** — with relative time ("2 hours ago") and exact timestamp
  - **Classification tag** — color-coded category: `rate_change`, `section_amendment`, `new_exemption`, `deadline_change`
- **Sorting**: Trust score desc → relevance desc → date desc (trust always wins)
- **Filter bar**: trust tier filter (Official only, Regulatory+, All sources), country filter (India/US), category filter
- **"Verify this" CTA** — every card has a "Open source" button that links directly to the original government/media URL
- **Deduplication**: Same news from multiple sources = collapsed into one card with "Confirmed by 3 sources" badge
- **New articles only** by default; toggle "Show archived" to see older items
- **Unread indicator** — dot/badge for articles since last open

### 5.9 Chat/qa page
- **Streaming responses** with source citations
- **Context sidebar** — shows which rules/documents are being referenced
- **Quick follow-up suggestions** — "Compare regimes", "Explain FTC", etc.
- **Agent-driven doc request** — when the agent needs specific info, it proactively asks:
  - "To explain your ₹25K deduction, can you upload your latest ESPP statement and RSU grant letter?"
  - "I see a large TDS entry — do you have a Form 1099 or brokerage statement for this?"
  - Shows a "documents needed" panel with checkmarks for what's available vs. what's missing
- **"Explain my pay this month"** button — agent scans all uploaded docs, identifies relevant ones, and produces a full breakdown of the pay slip with proof
- **"Explain this deduction"** — hover over any deduction line on the payslip, click to ask the agent: "Why is this ₹5,000 Professional Tax charged?" → agent responds with the state-specific rule

### 5.10 Reports page
- **Form viewer** — PDF rendered in-browser
- **Line-by-line explanation** — click any line to see the rule/calculation behind it
- **Download + export** — PDF, CSV, JSON
- **Historical year reports** — generate summary for any `TaxYear` with `status=historical`

### 5.11 Settings page
- **RAG management** — staging queue, promote, rollback snapshot
- **News sync** — view feed health (last success per RSS URL), manual "poll now", enable/disable third-party fallbacks
- **Residency status** — resident/NRI/NRPO toggle
- **Filing preferences** — year, jurisdiction, status
- **News source configuration** — per-feed poll interval, relevance threshold, trust filter level
- **Profile** — income type tags, countries, tax years
- **Dev only**: load TurboTax-style scenario fixture

### 5.12 News alerts panel (dashboard)
- Top 5 relevant rule changes with trust badges inline
- **Background sync status** (`news-sync-status.tsx`): "Last synced 4 min ago · 2 new notifications · RAG updated"
- Only shows items with trust_score >= configured threshold (default 0.5)
- Feed-type badge: `Notification` | `Circular` | `Press release` | `Verified by Taxmann`
- Each item: `[🏛️] Title` + "source" + "2 hours ago"
- Clicking opens the full news detail in a slide-over panel (not a new page)

### 5.13 Process visibility system (everywhere)
- **Pipeline tracker** — persistent sidebar or bottom bar showing active process progress
- **Event log** — real-time activity feed with filtering
- **Toast notifications** — non-blocking status updates
- **Loading states** — meaningful messages ("Analyzing 3 documents..."), not spinners
- **Error states** — clear recovery steps ("Document parsing failed. Try re-uploading or manually enter data.")
- **Retry mechanisms** — every process can be retried with progress feedback

---

## Phase 6: Reporting & Polish (Weeks 13-14)

**Goal**: Production-ready outputs, auditability, and deployment hygiene.

- PDF report generation (weasyprint or pdfkit) — supports **current and historical** tax years on cover sheet
- Export to CSV/Excel (calculation line items + prior-year comparison sheet)
- Audit trail (who changed what, when) — includes manual parsing overrides and `rule_version_id` on each calculation
- Input validation, error handling (unify with Phase 1 exception conventions)
- End-to-end test coverage including `test_cross_phase.py` interoperability suite
- CI/CD with automated tests (lint, unit, integration on PR; scheduled cross-phase tests)
- Docker compose for one-command setup
- **Performance baseline**: document parse p95, calculation p95, Q&A first-token latency logged in CI smoke tests

---

## Cross-Cutting Requirements

### Security & privacy
- Encrypt document files at rest; optional `APP_PASSWORD` on API
- Redact PAN, SSN, account numbers in logs and error traces
- `POST /api/dev/*` disabled when `ENV=production`
- User-facing disclaimer on dashboard and reports (not tax advice; not e-filing in v1)

### Interoperability testing
- **`test_cross_phase.py`**: scripted flows that touch multiple subsystems (upload → parse → historical TaxYear → calculate → report → Q&A cite)
- Run on every release candidate, not only unit-isolated tests
- Contract tests between frontend API client types and OpenAPI schema

### Continuous user feedback
- `POST /api/feedback/{area}` — areas: `parsing`, `calculation`, `news`, `qa` (thumbs + optional comment)
- Dashboard "Was this helpful?" on calculation and Q&A responses
- Periodic export for prompt/rule tuning (no PII in logs)

### Performance monitoring
- `app/core/metrics.py`: timers on parse, embed, calculate, agent round-trips
- `/health` and `/metrics` (Prometheus-compatible optional) for deployment
- Alert thresholds: parse > 120s, Q&A queue depth > 10, RAG update failure

---

## Key Design Decisions

1. **Tax engine is deterministic, AI is reasoning layer** — Always separate hard math (slabs, rates) from AI reasoning. The tax calculation engine must be 100% accurate and testable. LLMs provide document parsing, explanations, and recommendations.

2. **RAG is for law text; code is for math** — Slabs and rates live in `rule_versions.py` (tested). RAG holds statutory text and circulars for Q&A. Background RSS writes **staging** only; promote after review. QA always cites sources + `rule_version_id`.

3. **Process visibility is first-class** — Every multi-step process emits events, shows progress in real-time, handles errors gracefully, and allows retry. No black boxes.

4. **Exchange rate source** — Use RBI reference rate or OANDA API for USD→INR conversion at transaction date.

5. **DTAA + FTC is the critical complexity** — India-US DTAA article 15 (dependent personal services) and article 12/13 (royalties/capital gains) matter. Income taxed in US can get FTC in India, and vice versa.

6. **Status matters** — Residential status (resident, NRI, NRPO) determines which income is taxable in India. US citizens/green card holders are taxed on worldwide income regardless of residence. This must be captured upfront.

7. **UI is user-friendly by default** — Auto-detect what we can from documents, validate inline, save drafts, show progress, provide clear error messages, offer recovery options.

8. **Tax year follows the document** — Parsed `financial_year` on Form-16 / W-2 / prior ITR drives which rule pack runs. Current-year filing and historical reconciliation use the same engine with different `rule_version_id` pins.

9. **Trust is curated, relevance is personal** — Base `trust_score` is developer-set per source; user feedback adjusts relevance ranking only, not whether a source is "official."

10. **AIS + bank proofs are first-class** — India filing readiness requires AIS (not just 26AS), bank interest certificates, and cross-reconciliation before calculation is marked complete.

11. **Mocks enable TurboTax-grade CI** — Golden scenarios, synthetic docs, and recorded LLM outputs let every phase ship without real taxpayer data.

12. **Staging before promote** — No automatic deletion of production RAG chunks; notification ingest → staging → human promote → regression tests.

13. **Optimizer defers to engine** — Suggestions must pass a deterministic recalculation before shown as savings.

14. **India-first automation** — RSS + RAG promote pipeline is India-complete in v1; US is engine + manual uploads until v1.1 IRS feeds.

---

## Testing Strategy Summary

### Unit Tests
- Tax engine: every slab boundary, exemption, credit, edge case
- News classification accuracy against labeled examples
- RAG chunking and retrieval accuracy
- Document parser output validation
- Exchange rate calculation
- FTCA limit formula verification

### Integration Tests
- Full calculation pipeline with real data shapes
- Document upload → parse → extract → validate → save
- **AIS + 26AS + bank cert reconciliation** scenario from `mocks/scenarios/`
- RAG update: fetch → chunk → embed → index → retrieve
- News pipeline: **background worker poll** → RSS parse → PDF extract → classify → RAG action by feed type
- TurboTax-style: `load-scenario` → calculate → assert golden JSON within tolerance
- RSU vest → sell → calculate both jurisdictions + FTC
- SSE event flow: emit → subscribe → receive → display

### E2E Tests
- Complete user journey: dashboard → upload → parse → enter → calculate → optimize → chat → report
- Cross-browser testing for key flows
- Mobile responsiveness for document upload and income entry

### Test Infrastructure
- `conftest.py` with all fixtures
- `pytest` with `pytest-asyncio`, `pytest-cov`
- Mock LLM responses for deterministic testing
- Tax engine assertions against known-good calculators (ClearTax, IRS tools)
- Coverage target: 95%+ tax engine, 80%+ API
- CI on every PR, integration tests on schedule

---

## Verification

1. Run FastAPI backend: `uvicorn app.main:app --reload`
2. Pull Ollama model: `ollama pull llama3.1:8b`
3. Run test suite: `pytest --cov=app --cov-report=term-missing`
4. Tax engine: verify against ClearTax calculator for FY 2025-26
5. News monitoring: background worker polls all 4 official India RSS feeds; `test_rss_parser` PDF links; notification → staging `statutory` (not auto-promote)
6. Mock scenarios: `salaried_india_new_regime` end-to-end matches golden tax within tolerance
7. RAG update: trigger manually, verify rules loaded correctly, test retrieval
8. Document parsing: Form 16, **AIS**, **bank interest cert**, brokerage, salary slip
9. Full flow: upload → parse → enter income → calculate → view results
10. **Prior-year flow**: upload FY 2023-24 Form-16 → auto-detect year → calculate with 2023-24 slabs → compare to Form-16 TDS
11. **AIS reconciliation**: AIS Part-A TDS matches 26AS; AIS interest matches bank cert
12. Frontend: process visibility, documents checklist, news sync status, guided tour
13. RSU taxation: vesting price as ordinary income + capital gains on sale
14. Cross-jurisdiction: FTC calculation verified against known examples
15. Cross-phase interoperability suite passes in CI
16. Feedback endpoints store and retrieve without breaking ranking
