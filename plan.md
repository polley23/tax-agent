# Dual-Jurisdiction Tax Agent — Implementation Plan

## Context
Greenfield project in `/home/saptarshi/tax-agent/` (currently has only `merge_sort.py`). You want an AI-powered web app that ingests your financial documents (salary, RSU, stocks, investments), understands Indian + US tax rules, reasons over your situation via a local LLM, and generates tax filings with optimization recommendations.

**Tech stack**: Next.js (frontend) + FastAPI (backend) + LangChain + Ollama (local LLM) + SQLite → PostgreSQL

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
│   │   │   │   └── perquisites.py    # Per-employee stock, HRA, LTA
│   │   │   ├── us/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── income.py         # Standard deduction, brackets
│   │   │   │   ├── capital_gains.py  # Short/long-term CG rates
│   │   │   │   ├── rsu.py            # RSU vesting, ordinary income, 83(b)
│   │   │   │   ├── ftca.py           # Foreign Tax Credit (Form 1116)
│   │   │   │   └── filing_status.py  # Single/MFJ/MHO/QheadH
│   │   │   ├── dtaa.py               # DTAA analysis, FTC calculation
│   │   │   ├── rule_loader.py        # Load tax rules into RAG from authoritative sources
│   │   │   └── optimizer.py          # "old vs new", 83(b) timing, harvest
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── llm_client.py         # Ollama + LangChain LLM wrapper
│   │   │   ├── document_parser.py    # PDF/CSV/PDF ingestion, OCR
│   │   │   ├── agents/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── parsing_agent.py  # Extract income from documents
│   │   │   │   ├── calculation_agent.py # Run tax engine + explain results
│   │   │   │   ├── qa_agent.py       # Conversational tax Q&A
│   │   │   │   └── optimizer_agent.py# Tax optimization suggestions
│   │   │   ├── rag/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── vectorstore.py    # ChromaDB / FAISS embeddings
│   │   │   │   ├── chunking.py       # Tax rule text chunking strategy
│   │   │   │   ├── updater.py        # Incremental RAG updates from new sources
│   │   │   │   └── retriever.py      # Context retrieval for LLM agents
│   │   │   └── prompts/
│   │   │       ├── parsing_prompts.py
│   │   │       ├── reasoning_prompts.py
│   │   │       └── qa_prompts.py
│   │   ├── news/
│   │   │   ├── __init__.py
│   │   │   ├── monitors.py           # Continuous news monitoring service
│   │   │   ├── fetchers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── in_commerce.py    # incomeindia.gov.in circulars
│   │   │   │   ├── cbdt.py           # CBDT notifications
│   │   │   │   ├── irs.gov.py        # IRS notices, revenue procedures
│   │   │   │   ├── tax_news_api.py   # Financial news APIs (MoneyControl, ET, Bloomberg)
│   │   │   │   └── rss.py            # RSS feed aggregator
│   │   │   ├── parser.py             # Normalize news items to structured format
│   │   │   └── relevance.py          # Classify news → relevant tax rule changes
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── docs.py               # Upload, list, parse documents
│   │   │   ├── income.py             # CRUD for income entries
│   │   │   ├── calculation.py        # Run calculation, get results
│   │   │   ├── optimization.py       # Get optimization suggestions
│   │   │   ├── qa.py                 # Chat endpoint (SSE streaming)
│   │   │   ├── reports.py            # Generate ITR/1040 PDFs
│   │   │   ├── news.py               # News feeds, alerts, rule change dashboard
│   │   │   └── rag.py                # RAG management endpoints
│   │   ├── events/                   # Event-driven architecture for visibility
│   │   │   ├── __init__.py
│   │   │   ├── emitter.py            # Publish events (parsed, calculated, etc.)
│   │   │   └── listeners.py          # React to events (update UI, trigger downstream)
│   │   └── schemas/                  # Pydantic schemas (request/response)
│   │       ├── document.py
│   │       ├── income.py
│   │       ├── tax_result.py
│   │       └── event.py              # Event schema for pipeline tracking
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
│   │   │   ├── test_fetchers.py      # Each news source fetcher
│   │   │   ├── test_parser.py        # Normalization logic
│   │   │   └── test_relevance.py     # Classification accuracy
│   │   ├── integration/
│   │   │   ├── test_end_to_end.py    # Upload → parse → calculate → report
│   │   │   ├── test_rag_update.py    # Load rules → chunk → embed → retrieve
│   │   │   ├── test_news_pipeline.py # Fetch → parse → classify → notify
│   │   │   └── test_rsu_full.py      # RSU vest → sell → calculate both jurisdictions
│   │   └── conftest.py               # DB fixture, tax year fixture, income fixture
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
│   │   └── toast-notifications.tsx   # Auto-dismiss progress feedback
│   ├── hooks/
│ │   ├── use-events.ts              # SSE event subscription
│   │   ├── use-progress.ts           # Real-time progress tracking
│   │   └── use-api.ts               # Fetch with retry, error handling
│   ├── lib/
│   │   └── api.ts                    # API client wrapper
│   ├── next.config.ts
│   └── package.json
├── docker-compose.yml                # Backend + Ollama + DB
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

### 1.2 Data models (`db/models.py`)
```python
class TaxYear(Base):
    __tablename__ = "tax_years"
    id: int
    country: str  # "IN" | "US"
    financial_year: str  # "2025-26" | "2025"
    status: str  # "draft" | "filed"

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
    filename: str
    file_path: str
    mime_type: str
    uploaded_at: datetime
    status: str  # "uploaded" | "parsing" | "parsed" | "error"
    extracted_data: JSON  # JSON from LLM parsing
    progress: int  # 0-100 for real-time visibility

class Deduction(Base):
    __tablename__ = "deductions"
    id: int
    type: str  # "80C" | "80D" | "80E" | "standard_us" | "itemized_us"
    amount: Decimal
    section: str  # "Section 80C" | "Standard Deduction" etc.

class TaxCalculation(Base):
    __tablename__ = "tax_calculations"
    id: int
    tax_year_id: int
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
    source: str  # "in_commerce" | "cbdt" | "irs" | "moneycontrol"
    source_type: str  # "official_government" | "regulatory_body" | "financial_media" | "tax_blogger"
    trust_score: float  # 0.0-1.0 based on source authority (curated, never LLM-determined)
    title: str
    url: str
    published_at: datetime
    raw_content: str
    classified_as: str  # "rate_change" | "section_amendment" | "new_exemption"
    relevance_score: float  # relevance to user's profile
    confidence_score: float  # 0.0-1.0 — cross-source verification (multiple authoritative sources = higher)
    linked_rules: list  # rule IDs it affects
    processed: bool
    citations: JSON  # ["IRC Section 1", "Finance Bill 2025 Clause 12", etc.]

class NewsSource(Base):
    """Curated list of trusted sources with authority tiers — never auto-discovered."""
    __tablename__ = "news_sources"
    id: int
    name: str
    url_base: str
    source_type: str  # "official_government" | "regulatory_body" | "financial_media"
    trust_score: float  # set by developer, not by LLM
    country: str  # "IN" | "US"
    content_types: list  # ["circular", "notification", "revenue_procedure", "article"]
    last_verified: datetime
    active: bool

class RagIndex(Base):
    __tablename__ = "rag_index"
    id: int
    rule_id: str  # tax rule identifier
    text: str   # chunked text
    embedding_id: str
    metadata: JSON
    last_updated: datetime
    source: str  # "official_gazette" | "irc_section" | "circular"
```

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

**Key forms to generate**:
- ITR-2 (India, no business income) / ITR-1 (salary only)
- Form 1040, Form 8949 (stock sales), Form 1116 (FTC), Form 6781 (options)
- FBAR (FinCEN 114) if foreign accounts > $10K
- Form 8938 (FATCA) if thresholds met

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

**Integration Tests**:
- Full calculation flow: income entry → run calculation → verify output
- Document pipeline: upload → parse → extract → validate → save
- RAG update: load rules → chunk → embed → retrieve → verify relevance
- RSU full flow: vest → sell → calculate India tax + US tax + FTC → compare
- News pipeline: fetch → parse → classify → store → notify
- SSE event flow: event emitted → listener receives → UI updated

**Test infrastructure**:
- `conftest.py` shared fixtures: in-memory DB, tax year factory, income factory, mock LLM
- `pytest-asyncio` for async tests
- `httpx.AsyncClient` for API testing
- Tax engine assertions against known-good calculators (ClearTax, IRS interactive tools)
- Coverage target: 95%+ for tax engine, 80%+ for API

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
        "prompt": Extract equity award details (RSU/NSO/ISO) including vesting schedule, FMV, and grant terms..."
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

### 2.4 Ollama setup
```dockerfile
# docker-compose.yml service
ollama:
  image: ollama/ollama
  ports: ["11434:11434"]
  volumes: ["ollama_data:/root/.ollama"]
```

Suggested model: `llama3.1:8b` or `mistral:7b` (good balance of speed + accuracy for document parsing)

---

## Phase 3: News Monitoring & RAG Management (Weeks 5-6)

**Goal**: Continuously monitor tax rule changes, update RAG knowledge base, notify user.

### 3.1 News monitoring system (continuous, background task)
- **Scheduled fetches**: Every 6 hours via Celery/APScheduler
- **On open / last-seen fetch**: Every time the app starts (or the news page loads), fetch all articles published **since the last open timestamp** stored in a `SessionState` table:
  ```python
  class SessionState(Base):
      __tablename__ = "session_state"
      id: int
      key: str  # "last_news_fetch" | "last_seen_article_id"
      value: str  # ISO timestamp or article ID
      updated_at: datetime
  ```
  - On first open: fetch 7 days of history (configurable)
  - On subsequent opens: fetch `last_open_timestamp` → now
  - Store article IDs to deduplicate across scheduled + on-open fetches
  - After a successful on-open fetch: update `last_news_fetch` = now
  - If no new articles found: no UI change (silent, not annoying)
  - If new articles found: badge count increments + list appears in the news section
- **Trusted sources** (curated, never auto-discovered):
  - India: `incomeindia.gov.in` (notifications, circulars), CBDT notifications, Finance Bill updates
  - US: `irs.gov` (notices, revenue procedures, revenue rulings), Treasury releases
  - News: MoneyControl, ET, BloombergQuint (for market-impacting tax news)
  - RSS feeds: Tax law RSS aggregators
- **Classification**: LLM classifies each item into:
  - `rate_change` — slab rate or tax rate change
  - `section_amendment` — new/modified section
  - `new_exemption` — new deduction/exemption
  - `deadline_change` — due date or filing change
  - `no_impact` — irrelevant (stored but not flagged)
- **Relevance scoring**: Each item scored 0-1 on relevance to user's profile (residency, income types)
- **Alerts**: User gets notified in UI + optional email for high-relevance changes

### 3.2 RAG management
```
POST   /api/rag/status              # Current index size, last update time
POST   /api/rag/update              # Manual trigger to reload all tax rules
GET    /api/rag/rules               # List loaded rules
DELETE /api/rag/reset                # Reset and rebuild from scratch
```

**RAG update flow** (with full visibility):
```
User triggers "Update Tax Rules" → Event: rag_update.started
  → Fetch official sources → Event: rag_update.fetched (sources: X/Y)
  → Load new/changed rules → Event: rag_update.rules_loaded (rules: X new, Y changed)
  → Chunk rules → Event: rag_update.chunked (chunks: X)
  → Generate embeddings → Event: rag_update.embedded (progress: X%)
  → Update vector store → Event: rag_update.indexed (vectors: X)
  → Validate retrieval → Event: rag_update.complete
  → User notified: "3 rules updated, 1 section amended"
```

**RAG storage**: ChromaDB (in-memory for dev, persistent for prod) with rule metadata (source, effective date, rule_id).

### 3.3 API endpoints
```
POST   /api/calculation/run              # Run full tax calculation
GET    /api/calculation/{id}             # View calculation
POST   /api/optimization/run             # Get optimization suggestions
GET    /api/optimization/{id}            # View optimization
POST   /api/qa/chat                      # Chat (SSE streaming)
POST   /api/reports/generate             # Generate PDF
GET    /api/news/feed                    # Tax news feed
GET    /api/news/feed                    # Filterable: ?trust=official|regulatory|all&country=IN&category=rate_change
GET    /api/news/{id}                    # News detail with full citation block
GET    /api/news/alerts                  # High-relevance alerts
POST   /api/news/on-open-fetch           # Fetch since last open (auto-called on page load)
POST   /api/events/stream                # SSE event subscription
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
```python
# Parsing agent: extracts data from documents (Phase 2)
# Calculation agent: runs tax engine + explains results
# QA agent: answers general tax questions with RAG over tax code (always cites sources)
# Optimizer agent: suggests tax-saving strategies based on user's full profile
# PayExplainer agent: analyzes payslip deductions and produces line-by-line breakdown with proof
# DocRequester agent: identifies missing documents and proactively asks user to upload them
# TaxForecaster agent: projects full-year tax based on YTD data + what-if scenarios
```

# RAG documents for QA (always refreshed with latest rules):
# - India Income Tax Act sections (updated via RAG pipeline)
# - CBDT circulars (updated via news monitoring)
# - US IRC sections 1, 861, 862, 911, 912, 956-964, 1042, 1116
# - DTAA agreements (India-US treaty)
# - Relevant case laws
# - Recent Finance Bill changes
```

### 4.2 Q&A agent design
- Always retrieves from updated RAG before answering
- Citations included in responses (source URL, section number, date)
- "Last updated" timestamp visible in UI
- If RAG has no relevant docs, agent says so instead of hallucinating

### 4.3 Agent-driven doc request
- **Missing doc detection**: agent analyzes current understanding and identifies gaps:
  - "I can see ₹50K deducted but need your ESPP statement to explain the breakdown"
  - "You have ₹80K extra TDS — do you have a brokerage 1099-B for this month?"
  - "Your income structure changed — I need your updated RSU grant letter"
- **Smart doc suggestions**: agent suggests what to upload and why:
  - "Upload your ESPP confirmation → I can explain the discount tax and Section 17(2) valuation"
  - "Upload Form 1099-DIV → I can explain ordinary dividend vs qualified dividend tax"
  - "Upload 80C investment proofs → I can calculate your full deduction"
- **Doc availability tracking**: panel showing what docs are uploaded vs. what's needed
- **"Explain this deduction" flow**: user hovers over any pay slip line → agent identifies the likely source document → asks user to confirm or upload if missing

### 4.4 PayExplainer agent
- When a payslip is uploaded, this agent analyzes every deduction line
- Matches each deduction to: (1) applicable law, (2) user's document proof, (3) calculation formula
- Handles special cases: ESPP discount tax, RSU withholding, stock grant tax, Section 17(2) employer contribution
- Cross-references with uploaded 1099-B, grant letters, ESPP confirmations to produce proof
- If a deduction has no matching document, flags it: "₹25,000 ESPP deduction found — need ESPP statement to explain"

### 4.5 TaxForecaster agent
- Builds YTD model from pay slips + 1099s + 26AS
- Projects full-year income, deductions, effective tax rate
- Simulates what-if scenarios: bonus, investment change, stock vesting timing, regime change
- Produces deadline alerts: advance tax, 80C deadline, estimated tax payment due dates

---

## Phase 5: Frontend UI (Weeks 9-12)

**Goal**: User-friendly, fully transparent UI with real-time process visibility.

### 5.1 Dashboard
- **Income summary card** — total income by source, by jurisdiction, by year
- **Tax liability card** — current year liability, comparison with prior year
- **Regime selector** — one-click old vs new comparison
- **News alerts panel** — top 5 relevant rule changes
- **Recent activity feed** — last uploads, calculations, document parses
- **Status badges** — "Tax year 2025-26: 3 documents pending review"

### 5.2 Document management page
- **Drag-and-drop upload** with progress bars
- **Document cards** showing: name, type, status (uploaded/parsing/parsed/error), progress %, extracted data preview
- **Confirmation step** — extracted data shown as editable table before committing to income sources
- **Re-parse** button for documents that were parsed incorrectly
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
  - **Other**: Prior year ITR, 26AS/AIS, TDS certificates
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

### 5.7 Reports page
- **Form viewer** — PDF rendered in-browser
- **Line-by-line explanation** — click any line to see the rule/calculation behind it
- **Download + export** — PDF, CSV, JSON

### 5.8 Settings page
- **RAG management** — "Update Tax Rules" button with progress
- **Residency status** — resident/NRI/NRPO toggle
- **Filing preferences** — year, jurisdiction, status
- **News source configuration** — enable/disable sources, relevance threshold, trust filter level
- **Profile** — income type tags, countries, tax years

### 5.9 News alerts panel (dashboard)
- Top 5 relevant rule changes with trust badges inline
- Only shows items with trust_score >= configured threshold (default 0.5)
- Each item: `[🏛️] Title` + "source" + "2 hours ago"
- Clicking opens the full news detail in a slide-over panel (not a new page)

### 5.10 Process visibility system (everywhere)
- **Pipeline tracker** — persistent sidebar or bottom bar showing active process progress
- **Event log** — real-time activity feed with filtering
- **Toast notifications** — non-blocking status updates
- **Loading states** — meaningful messages ("Analyzing 3 documents..."), not spinners
- **Error states** — clear recovery steps ("Document parsing failed. Try re-uploading or manually enter data.")
- **Retry mechanisms** — every process can be retried with progress feedback

---

## Phase 6: Reporting & Polish (Weeks 13-14)

- PDF report generation (weasyprint or pdfkit)
- Export to CSV/Excel
- Audit trail (who changed what, when)
- Input validation, error handling
- End-to-end test coverage
- CI/CD with automated tests
- Docker compose for one-command setup

---

## Key Design Decisions

1. **Tax engine is deterministic, AI is reasoning layer** — Always separate hard math (slabs, rates) from AI reasoning. The tax calculation engine must be 100% accurate and testable. LLMs provide document parsing, explanations, and recommendations.

2. **RAG is always current** — Tax rules are never hardcoded in prompts. RAG is the single source of truth and is updated via the news monitoring pipeline. QA agent always cites retrieved sources.

3. **Process visibility is first-class** — Every multi-step process emits events, shows progress in real-time, handles errors gracefully, and allows retry. No black boxes.

4. **Exchange rate source** — Use RBI reference rate or OANDA API for USD→INR conversion at transaction date.

5. **DTAA + FTC is the critical complexity** — India-US DTAA article 15 (dependent personal services) and article 12/13 (royalties/capital gains) matter. Income taxed in US can get FTC in India, and vice versa.

6. **Status matters** — Residential status (resident, NRI, NRPO) determines which income is taxable in India. US citizens/green card holders are taxed on worldwide income regardless of residence. This must be captured upfront.

7. **UI is user-friendly by default** — Auto-detect what we can from documents, validate inline, save drafts, show progress, provide clear error messages, offer recovery options.

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
- RAG update: fetch → chunk → embed → index → retrieve
- News pipeline: fetch → parse → classify → notify
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
5. News monitoring: verify fetch from 3+ sources, classification accuracy
6. RAG update: trigger manually, verify rules loaded correctly, test retrieval
7. Document parsing: test with Form 16, brokerage statement, salary slip
8. Full flow: upload → parse → enter income → calculate → view results
9. Frontend: test all process visibility components, error states, retry flows
10. RSU taxation: vesting price as ordinary income + capital gains on sale
11. Cross-jurisdiction: FTC calculation verified against known examples
