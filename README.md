# Finance ETL Dashboard

A small, deployable "CSV → Database → Dashboard" mini data platform.

- **Upload a CSV** of transactions
- **Validate + normalize** (date/description/amount)
- **Auto-categorize** using simple rules (no paid APIs)
- Store in **Postgres**
- Explore results in a **Streamlit dashboard**
- Access everything via a **FastAPI** REST API

---

## What this project demonstrates

- Building a containerized backend service (FastAPI)
- Data ingestion + validation
- Database modeling + migrations (SQLAlchemy + Alembic)
- Typed API responses (Pydantic response models)
- API key authentication
- Queryable APIs (filters + pagination)
- Basic analytics endpoints (summaries)
- A simple but useful dashboard UI (Streamlit)
- Test suite (pytest) with CI (GitHub Actions)
- One-command local deployment (Docker Compose)

---

## Tech Stack

- Python 3.11
- FastAPI + Uvicorn
- Pydantic (request/response validation)
- SQLAlchemy + Alembic (ORM + migrations)
- Postgres
- Streamlit
- pytest
- Docker + Docker Compose

---

## Quickstart (Docker)

### 1) Create `.env`
Copy the example config:

**Windows PowerShell**
```powershell
Copy-Item .env.example .env
```

**macOS/Linux**
```bash
cp .env.example .env
```

Then edit `.env` and set `API_KEY` to a secret of your choice (or leave it empty to disable auth).

### 2) Start the stack

From the repo root:
```bash
docker compose up --build
```

### 3) Open the app
- Dashboard: http://localhost:8501
- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health


### 4) Stop the stack
To stop the containers:
```bash
docker compose down
```

### 5) Reset the database (optional)
This project stores Postgres data in a Docker volume. To remove it completely:

```bash
docker compose down -v
```

### 6) Try the demo
1. Open the dashboard: http://localhost:8501
2. Click **Load demo dataset** in the sidebar
3. You should see charts and a transactions table populate

You can also explore the API docs at: http://localhost:8000/docs


### 7) Ingest your own CSV
Upload a CSV in the dashboard sidebar and click **Ingest CSV**.

Minimum required columns:
- `date`
- `description`
- `amount`

Example:
```csv
date,description,amount
2026-01-01,Aldi Grocery,-23.50
2026-01-02,Netflix,-12.99
2026-01-03,Uber,-8.40
```

### 8) Authentication

API endpoints (except `/health`) are protected by an API key when `API_KEY` is set in `.env`.

Pass the key via the `X-API-Key` header:
```bash
curl -H "X-API-Key: your-secret" "http://localhost:8000/transactions?limit=10"
```

If `API_KEY` is empty or unset, authentication is disabled and all endpoints are open.

The dashboard reads the same `API_KEY` from the environment and includes it automatically.

### 9) Use the API
Open Swagger UI:
- http://localhost:8000/docs

All responses are validated with Pydantic models, so the Swagger docs show the exact response shape for every endpoint.

Endpoints:
- `POST /ingest` — upload CSV as `file`
- `GET /transactions` — pagination + filters (category, date range, merchant, amount)
- `GET /summary/by-category`
- `GET /summary/over-time?granularity=day|month`
- `GET /health` — health check (no auth required)

### 10) Running tests

```bash
cd api
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```

Tests cover:
- CSV ingestion (multiple formats, delimiters, deduplication)
- Transaction filtering (category, date range, merchant search)
- Summary endpoints
- Auto-categorization rules
- Authentication (key rejection + acceptance)
- Error handling (bad file types, missing columns)

### 11) Development
Rebuild after changes:
```bash
docker compose build api
docker compose build dashboard
docker compose up -d
```

View logs:
```bash
docker compose logs api --tail 100
docker compose logs dashboard --tail 100
docker compose logs db --tail 100
```

Run migrations:
```bash
docker compose exec api alembic upgrade head
```

### 12) Project structure
```text
finance-etl-dashboard/
  api/
    app/
      main.py          # FastAPI routes
      schemas.py       # Pydantic response models
      models.py        # SQLAlchemy models
      db.py            # Database engine/session
      deps.py          # Dependencies (auth, db session)
      settings.py      # Environment config
      categorizer.py   # Rule-based categorization
    tests/
      conftest.py
      test_ingest.py
      test_endpoints.py
      test_categorizer.py
    migrations/
    alembic.ini
    Dockerfile
    requirements.txt
  dashboard/
    app.py
    Dockerfile
    requirements.txt
  data/
    sample_transactions.csv
  compose.yaml
  .env.example
  README.md
```

### 13) License
MIT License (see `LICENSE`).
