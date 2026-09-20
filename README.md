# US Government Spending & Procurement Analytics

SQL Server + Power BI analytics over U.S. federal procurement data (USAspending.gov), with a planned AI natural-language layer via FastAPI + Groq.

**Architecture (Phase 2):**

```
USAspending data → SQL Server (USAspendingDB, ~4.14M rows) → SQL views → Power BI
                                              ↘ FastAPI (read-only) → JSON API
```

SQL Server is the source of truth. Power BI is dashboard-only. Azure SQL will replace `localhost` later via env vars.

---

## Phase 3 — Read-only text-to-SQL layer

Provides a safe, production-style Python layer over the **existing** `USAspendingDB` (`localhost`, SQL Server 2025). The application does not write to the database.

**App files:**

- `app/config.py` — env via `python-dotenv` (`SQL_SERVER`, `SQL_DATABASE`, `SQL_DRIVER`, `API_HOST/PORT`, optional `SQL_USERNAME/PASSWORD`). No hardcoded secrets. `TrustServerCertificate=yes` for local dev; Azure just needs different `SQL_SERVER`.
- `app/database.py` — `pyodbc` helper: parameterized queries only, read-only guard (`SELECT`/`WITH` only, blocks `INSERT/UPDATE/DELETE/DROP/...`), 30s connection/query timeout, 500-row cap, sanitized errors, no credential logging.
- `app/main.py` — FastAPI:
  - `GET /` → service info
  - `GET /health` → `{"status":"healthy","database":"reachable"}` (or 503 if SQL unreachable); safe config included, no secrets
  - `GET /api/agency-spending[?fiscal_year=YYYY&limit=N]` → queries existing `dbo.vw_AgencySpending` (or filtered grouping on `dbo.Transactions` when `fiscal_year` given), returns `{count, data:[{agency, total_obligations}], source, limit}`
  - `POST /api/ask` → Groq text-to-SQL over the six verified production views, with AST validation, `TOP 500`, one database-error retry, and per-IP rate limiting.
- `app/text2sql/schema_context.py` — live production view whitelist and `INFORMATION_SCHEMA` column prompt.
- `app/text2sql/validator.py` — `sqlglot` T-SQL safety validation; rejects DML/DDL, system objects, comments, and stacked statements.
- `app/text2sql/pipeline.py` — question → Groq → validator → read-only SQL execution.
- `ui/` — React/Vite browser client for `POST /api/ask`; the development server proxies `/api` to FastAPI and the production build is served at `/ui/`.

### Text-to-SQL configuration

Set these values in the local `.env` file:

```powershell
LLM_PROVIDER=groq
LLM_API_KEY=<your-groq-key>
LLM_MODEL=openai/gpt-oss-20b
```

The live database currently exposes these six approved views: `vw_AgencySpending`, `vw_AwardTypeSpending`, `vw_FederalSpendingByYear`, `vw_PeriodSpendingChange`, `vw_RecipientSpendingRank`, and `vw_Top10RecipientConcentration`. The repository's other view files describe a separate, newer schema and are not used by text-to-SQL.

### React UI

```powershell
cd ui
npm install
npm run dev
```

The Vite development UI runs at `http://127.0.0.1:5173/` and proxies API requests to FastAPI on port 8000. For the FastAPI-served production bundle:

```powershell
cd ui
npm run build
cd ..
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/ui/`.

### Safety notes

- The LLM never receives credentials.
- Generated SQL is parsed with `sqlglot` before execution.
- Only approved `dbo` views are allowed; direct access to `Transactions`, system objects, and unknown views is rejected.
- Only one read-only statement is allowed, with a maximum `TOP 500`.
- Database errors are sanitized before returning to clients.
- `.env` and API keys must never be committed.

**Existing SQL views (prod, not modified):**

`vw_AgencySpending`, `vw_AwardTypeSpending`, `vw_FederalSpendingByYear`, `vw_PeriodSpendingChange`, `vw_RecipientSpendingRank`, `vw_Top10RecipientConcentration` (plus Phase-1 design docs in `sql/views/` / `docs/architecture/` — not applied to prod).

---

## Setup

### 1. Configure SQL Server connection

```powershell
Copy-Item .env.example .env
# Edit .env — for local Windows auth, leave SQL_USERNAME/PASSWORD empty:
# SQL_SERVER=localhost
# SQL_DATABASE=USAspendingDB
# SQL_DRIVER=ODBC Driver 18 for SQL Server
# For Azure SQL / SQL auth: set SQL_USERNAME, SQL_PASSWORD
```

`.env` is gitignored. Never commit secrets. `app/config.py` loads it via `python-dotenv`.

Requires ODBC Driver 17 or 18 for SQL Server (`Get-OdbcDriver`).

### 2. Install & run

```powershell
pip install -r requirements.txt
# requirements: fastapi, uvicorn, pydantic, python-dotenv, pyodbc, etc.
# For tests: pip install pytest httpx

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# or: python -m uvicorn app.main:app --reload
```

`API_HOST` / `API_PORT` from `.env` are used if you wire `uvicorn` via config; `uvicorn` flags above override.

### 3. Test endpoints (no DB required for health check logic, but live DB gives real data)

```powershell
# Health — does not expose credentials
curl http://127.0.0.1:8000/health
# → {"status":"healthy","database":"reachable","config":{...}}  or 503 if SQL unreachable

# Agency spending (view)
curl http://127.0.0.1:8000/api/agency-spending
# → {"count":1,"data":[{"agency":"General Services Administration","total_obligations":...}],"source":"vw_AgencySpending","limit":20}

# Filtered by fiscal year (parameterized, read-only)
curl "http://127.0.0.1:8000/api/agency-spending?fiscal_year=2021&limit=10"

# Interactive docs
# http://127.0.0.1:8000/docs
# Browser client
# http://127.0.0.1:8000/ui/

# Optional live evaluation (requires Groq and SQL Server)
$env:RUN_TEXT2SQL_EVAL = "1"

  ### Deploy to Render

  This repository includes `render.yaml` for a single Render web service. The
  service builds the Vite UI and serves it from FastAPI at `/ui/`.

  1. Create a Render Web Service from this GitHub repository.
  2. Select the `main` branch. Render can use the committed `render.yaml`
    settings automatically.
  3. Add the values from `.env.example` as Render environment variables. Do
    not upload `.env`.
  4. Set `SQL_SERVER` and the related database variables to a reachable remote
    SQL Server. A local `localhost` database is not reachable from Render.
  5. Set `LLM_API_KEY` (or `GROQ_API_KEY`) if text-to-SQL is enabled.

  After deployment, open `/ui/`. The root URL is a lightweight service check;
  `/health` also verifies database connectivity and may return `503` until the
  remote database is configured.
pytest -q tests/text2sql_eval.py -s
```

### 4. Run tests

```powershell
pytest -v
# 16 tests — all mocked, no prod DB needed:
#   tests/test_health.py
#   tests/test_agency_spending.py
#   tests/test_database.py  (read-only guard, timeout/row-cap, error handling)
```

**Live DB smoke test (requires `USAspendingDB` reachable):**

```powershell
python -c "from app.database import check_connection; print(check_connection())"
python -c "import pyodbc; print(pyodbc.drivers())"
```

---

## Scope notes (Phase 2)

Done: FastAPI + safe DB layer + one read-only endpoint + tests + docs.  
Deferred: Groq/LLM, `/ask`, text-to-SQL, Streamlit, RAG/embeddings, anomaly detection, Power BI changes, Azure migration, Docker.  
Prod DB (4.14M rows) is never modified by the app.

## Docs

- `docs/architecture/schema.md` — table/col notes & future design (Phase-1 docs)
- `docs/architecture/views.md` — AI-ready view specs
- `sql/analysis/verification_queries.sql` — manual intent queries against prod views
