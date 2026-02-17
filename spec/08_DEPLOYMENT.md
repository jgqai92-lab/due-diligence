# Deployment Plan

## Deployment Strategy

**Local-first, self-hosted.** The Skeptical Analyst runs on the user's machine. No cloud infrastructure, no monthly hosting fees. The only external dependency is the Claude API (paid) and Alpaca Paper Trading API (free).

---

## Architecture

Two processes running locally:

| Process | Technology | Port | Purpose |
|---------|-----------|------|---------|
| **Backend** | Python FastAPI + Uvicorn | 8000 | yfinance data, forensic calcs, SQLite, Claude API |
| **Frontend** | Next.js (Node.js) | 3000 | Commercial-grade UI, calls backend API |

**Orchestration:** Docker Compose (recommended) or manual process management.

---

## Environment Variables

### Required `.env` File

```bash
# Claude API — ONLY paid dependency
ANTHROPIC_API_KEY="sk-ant-..."

# Alpaca Paper Trading API — FREE tier
ALPACA_API_KEY="PK..."
ALPACA_SECRET_KEY="..."

# Alpaca Base URL — Paper Trading ONLY
ALPACA_BASE_URL="https://paper-api.alpaca.markets"
```

**That's it.** Three API keys. No database connection strings (SQLite is a local file). No hosting credentials. No FMP key.

### `.env` Location
- Root of project: `./.env`
- Loaded by both backend (python-dotenv) and frontend (Next.js built-in)

### Security
- `.env` is listed in `.gitignore` — never committed
- `.env.example` provided with placeholder values for onboarding
- All API calls to external services made from Python backend only
- Frontend never touches API keys

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm or pnpm
- Docker + Docker Compose (optional but recommended)

### Option 1: Docker Compose (Recommended)

```bash
# Clone and configure
git clone <repo-url>
cd skeptical-analyst
cp .env.example .env
# Edit .env with your API keys

# Start everything
docker-compose up

# Application available at:
#   Frontend: http://localhost:3000
#   Backend:  http://localhost:8000
#   API Docs: http://localhost:8000/docs (FastAPI auto-generated)
```

**docker-compose.yml:**
```yaml
version: "3.8"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data          # SQLite database persistence
      - ./.env:/app/.env:ro       # Environment variables
    environment:
      - PYTHONUNBUFFERED=1

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
```

### Option 2: Manual Process Management

```bash
# Terminal 1: Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head  # Run database migrations
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

---

## Database

### SQLite Configuration
- **File:** `./data/skeptical_analyst.db`
- **Created automatically** on first run via Alembic migrations
- **WAL mode** enabled for concurrent read/write
- **No connection string** — just a file path

### Migrations
```bash
# Run migrations (creates tables if they don't exist)
cd backend
alembic upgrade head

# Create a new migration after schema change
alembic revision --autogenerate -m "description"
```

### Backup
```bash
# Just copy the file
cp ./data/skeptical_analyst.db ./data/skeptical_analyst.backup.db
```

### Reset (Development)
```bash
# Delete and recreate
rm ./data/skeptical_analyst.db
alembic upgrade head
```

---

## Project Structure

```
skeptical-analyst/
├── .env                    # API keys (git-ignored)
├── .env.example            # Template with placeholder values
├── .gitignore
├── docker-compose.yml
├── README.md
├── PRD.md
├── spec/                   # Specification documents
│   ├── 00_MISSION.md
│   ├── 01_REQUIREMENTS.md
│   ├── 02_ARCHITECTURE.md
│   ├── 03_API_SPEC.md
│   ├── 04_DATABASE_SCHEMA.md
│   ├── 05_DESIGN_SYSTEM.md
│   ├── 06_COMPONENT_SPEC.md
│   ├── 07_TESTING_STRATEGY.md
│   └── 08_DEPLOYMENT.md
├── data/                   # SQLite database (git-ignored)
│   └── skeptical_analyst.db
├── backend/                # Python FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── config.py           # Settings from .env
│   │   ├── database.py         # SQLAlchemy + SQLite setup
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── routers/            # API route handlers
│   │   │   ├── analyze.py
│   │   │   ├── search.py
│   │   │   ├── portfolio.py
│   │   │   └── alerts.py
│   │   ├── services/           # Business logic
│   │   │   ├── yfinance_service.py    # yfinance data fetching + caching
│   │   │   ├── forensic_engine.py     # M-Score, Z-Score, Rule of 40, Magic Number
│   │   │   ├── citation_service.py    # Citation generation
│   │   │   ├── claude_service.py      # Claude API report generation
│   │   │   └── alpaca_service.py      # Alpaca Paper Trading integration
│   │   └── utils/
│   │       ├── calculations.py        # Pure math functions
│   │       └── validators.py          # Input validation
│   └── tests/
│       ├── unit/
│       │   ├── test_beneish.py
│       │   ├── test_altman.py
│       │   ├── test_saas_metrics.py
│       │   └── test_citations.py
│       ├── integration/
│       │   ├── test_yfinance.py
│       │   ├── test_api_analyze.py
│       │   └── test_api_portfolio.py
│       └── conftest.py
└── frontend/               # Next.js
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── next.config.ts
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx              # Dashboard / landing
    │   ├── analyze/
    │   │   └── [ticker]/
    │   │       └── page.tsx      # Forensic analysis page
    │   ├── portfolio/
    │   │   └── page.tsx          # Portfolio management
    │   ├── alerts/
    │   │   └── page.tsx          # Alert history
    │   └── globals.css
    ├── components/
    │   ├── ui/                   # shadcn/ui base components
    │   ├── ticker-search.tsx
    │   ├── forensic-score-card.tsx
    │   ├── beneish-panel.tsx
    │   ├── altman-panel.tsx
    │   ├── saas-metrics-panel.tsx
    │   ├── citation-tooltip.tsx
    │   ├── forensic-report.tsx
    │   ├── portfolio-table.tsx
    │   ├── alert-banner.tsx
    │   ├── dashboard-layout.tsx
    │   ├── red-flag-badge.tsx
    │   ├── data-freshness.tsx
    │   └── skeleton-loader.tsx
    ├── lib/
    │   ├── api-client.ts         # HTTP client for FastAPI backend
    │   ├── types.ts              # TypeScript interfaces
    │   └── utils.ts              # Formatting, color helpers
    └── __tests__/
        ├── components/
        └── e2e/                  # Playwright tests
```

---

## Cost Summary

| Component | Cost |
|-----------|------|
| yfinance (Python library) | $0 |
| SQLite (local database) | $0 |
| Alpaca Paper Trading API | $0 |
| Next.js (open source) | $0 |
| FastAPI (open source) | $0 |
| Docker (open source) | $0 |
| **Claude API (Anthropic)** | **Usage-based (~$10-50/mo)** |
| **Total** | **~$10-50/mo** |

---

## Troubleshooting

### Backend won't start
- Verify Python 3.11+ installed: `python --version`
- Verify .env exists with valid API keys
- Check `./data/` directory exists (created by Docker volume or manually)
- Run `alembic upgrade head` if database doesn't exist

### Frontend won't start
- Verify Node.js 18+ installed: `node --version`
- Run `npm install` if node_modules missing
- Ensure backend is running on port 8000

### yfinance rate limited
- Data is cached in SQLite for 24 hours
- If hitting limits, wait and retry — yfinance has no official rate limit documentation
- Check `cached_financials` table for existing data

### Claude API errors
- Verify `ANTHROPIC_API_KEY` is valid and has credits
- Check Anthropic status page for outages
- Reports will fail with `CLAUDE_ERROR` — forensic metrics still display without the narrative report

### Alpaca connection issues
- Verify `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` are for Paper Trading (not live)
- Ensure `ALPACA_BASE_URL` is `https://paper-api.alpaca.markets`
- Portfolio valuation will show "Price unavailable" if Alpaca is unreachable

---

**Created:** 2026-01-30
**Last Updated:** 2026-01-30
**Owner:** @Chief_Architect
