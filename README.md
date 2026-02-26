# Finance ETL Dashboard

A small, deployable “CSV → Database → Dashboard” mini data platform.

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
- Queryable APIs (filters + pagination)
- Basic analytics endpoints (summaries)
- A simple but useful dashboard UI (Streamlit)
- One-command local deployment (Docker Compose)

---

## Tech Stack

- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy
- Alembic (migrations)
- Postgres
- Streamlit
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


If you started it in the background, you can still stop it anytime with:
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


### 8) Use the API (optional)
Open Swagger UI:
- http://localhost:8000/docs

Useful endpoints:
- `POST /ingest` (upload CSV as `file`)
- `GET /transactions` (pagination + filters)
- `GET /summary/by-category`
- `GET /summary/over-time?granularity=day|month`


Example:
```bash
curl "http://localhost:8000/transactions?limit=10"
```


### 9) Development
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

### 10) Project structure
```text
finance-etl-dashboard/
  api/
    app/
      main.py
      db.py
      models.py
      deps.py
      categorizer.py
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


### 11) License
MIT License (see `LICENSE`).






















