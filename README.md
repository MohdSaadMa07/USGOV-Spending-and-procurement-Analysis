# US Government Spending & Procurement Analysis

Read-only analytics for public U.S. federal spending data from [USAspending.gov](https://www.usaspending.gov/). The project combines a SQL Server analytical layer, a Power BI report, and a FastAPI + React query desk that turns plain-language questions into validated read-only SQL.

## Live Demo

**Application:** [Open the live query desk](https://gopher-wielder-banter.ngrok-free.dev/ui/)

The demo currently runs from a local machine through a reserved free ngrok domain. SQL Server, FastAPI, and ngrok must be running for the link to work. ngrok may display a free-plan warning page before the application loads.

**Repository:** [MohdSaadMa07/USGOV-Spending-and-procurement-Analysis](https://github.com/MohdSaadMa07/USGOV-Spending-and-procurement-Analysis)

## What This Project Demonstrates

- Public-sector procurement and spending analysis over approximately 4.14 million transaction rows.
- SQL Server views designed for safe analytical access.
- Power BI reporting for executive-level trends, concentration, recipients, and award types.
- Natural-language questions translated into T-SQL by Groq and checked before execution.
- A read-only API with parameterized queries, SQL validation, row limits, timeouts, sanitized errors, and rate limiting.
- A React interface with two focused workspaces: **Query Desk** and **Power BI Visuals**.

## Application Tabs

### 1. Query Desk

Ask questions such as:

- Show total spending by fiscal year.
- Which agencies have the highest total obligations?
- What percentage is concentrated among the top ten recipients?

The request flows through:

```text
Question -> Groq SQL generation -> sqlglot validation -> approved SQL view -> results
```

Only the approved analytical views are available to the text-to-SQL layer. The application does not write to the database.

### 2. Power BI Visuals

The second tab documents the Power BI report visual by visual. It includes:

- Total federal obligations
- Top-10 recipient concentration
- Unique vendors
- Top recipients ranked table
- Top recipients bar chart
- Fiscal-year trend
- Period-over-period spending change
- Award-type mix

The report snapshot is captured from the Power BI report and shown in the application for visitors who do not have Power BI access.

## Screenshots

### Query Desk

> Screenshot placeholder: add a full-page Query Desk capture at `ui/public/query-desk.png`, then embed it here with `![Query Desk screenshot](ui/public/query-desk.png)`.

### Power BI Visuals tab

![Power BI Visuals screenshot](ui/public/MAIN%20HEADER%20IMAGE.png)

The visual gallery uses the following report captures:

| Visual | Screenshot |
| --- | --- |
| Total federal obligations | [01-total-obligations.png](ui/public/01-total-obligations.png) |
| Top-10 concentration | [02-top10-concentration.png](ui/public/02-top10-concentration.png) |
| Unique vendors | [03-unique-vendors.png](ui/public/03-unique-vendors.png) |
| Top recipients bars | [04-top-recipients-bars.png](ui/public/04-top-recipients-bars.png) |
| Fiscal-year trend | [05-fiscal-year-trend.png](ui/public/05-fiscal-year-trend.png) |
| Top recipients table | [06-top-recipients-table.png](ui/public/06-top-recipients-table.png) |
| Period change | [07-period-change.png](ui/public/07-period-change.png) |
| Award type | [08-award-type.png](ui/public/08-award-type.png) |

## Architecture

```text
USAspending.gov public data
          |
          v
SQL Server: USAspendingDB
          |
          +--> approved analytical views --> Power BI report
          |
          +--> FastAPI read-only API --> React/Vite UI
                                      |
                                      +--> Query Desk
                                      +--> Power BI Visuals
```

### Backend

- `app/main.py` - FastAPI application and API routes.
- `app/database.py` - pyodbc connection and read-only query execution.
- `app/config.py` - environment-based configuration.
- `app/text2sql/schema_context.py` - approved view whitelist and live column metadata.
- `app/text2sql/validator.py` - sqlglot T-SQL validation and safety checks.
- `app/text2sql/pipeline.py` - question, SQL generation, validation, execution, and retry flow.

### Frontend

- `ui/src/main.jsx` - Query Desk and Power BI Visuals tabs.
- `ui/src/styles.css` - interface styling.
- `ui/public/` - Power BI screenshots and public static assets.

## Approved Analytics Views

The text-to-SQL layer is restricted to these views:

- `dbo.vw_AgencySpending`
- `dbo.vw_AwardTypeSpending`
- `dbo.vw_FederalSpendingByYear`
- `dbo.vw_PeriodSpendingChange`
- `dbo.vw_RecipientSpendingRank`
- `dbo.vw_Top10RecipientConcentration`

## Run Locally

### Prerequisites

- Python 3.10+
- Node.js and npm
- SQL Server with `USAspendingDB` and the approved views
- Microsoft ODBC Driver 17 or 18 for SQL Server
- Optional: Groq API key for text-to-SQL

### Configure the environment

```powershell
Copy-Item .env.example .env
```

For local Windows Authentication, leave these values empty:

```dotenv
SQL_SERVER=localhost
SQL_DATABASE=USAspendingDB
SQL_DRIVER=ODBC Driver 18 for SQL Server
SQL_USERNAME=
SQL_PASSWORD=
```

For the LLM layer, add your own key locally:

```dotenv
LLM_PROVIDER=groq
LLM_API_KEY=your-key-here
LLM_MODEL=openai/gpt-oss-20b
```

### Install dependencies

```powershell
pip install -r requirements.txt
npm install --prefix ui
```

### Start the application

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open:

- UI: http://127.0.0.1:8000/ui/
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

For frontend development with hot reload:

```powershell
npm run dev --prefix ui
```

## Public Demo Without Paid Hosting

Because the database is local, Render cannot reach `SQL_SERVER=localhost`. For a free live demo, expose only FastAPI through a tunnel. Never expose SQL Server port 1433.

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
ngrok http --domain=gopher-wielder-banter.ngrok-free.dev 8000
```

This preserves the same public URL, but the local computer, SQL Server, FastAPI, internet connection, and ngrok process must remain available.

## Render Deployment

The repository includes `render.yaml` and `Dockerfile` for a single Render web service. The container installs Microsoft ODBC Driver 18 and builds the React UI.

Render can host the application container, but a local SQL Server is not reachable from Render. To run live queries on Render, configure a reachable hosted SQL Server and SQL authentication in Render environment variables:

```text
SQL_SERVER=your-reachable-server
SQL_DATABASE=USAspendingDB
SQL_DRIVER=ODBC Driver 18 for SQL Server
SQL_USERNAME=your-read-only-login
SQL_PASSWORD=your-password
SQL_TRUST_SERVER_CERTIFICATE=yes
LLM_PROVIDER=groq
LLM_API_KEY=your-new-key
LLM_MODEL=openai/gpt-oss-20b
```

The Power BI report does not need to be recreated for the current local demo. Moving the database to another provider later may require updating its data source and refresh configuration.

## API Examples

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/agency-spending
curl "http://127.0.0.1:8000/api/agency-spending?fiscal_year=2021&limit=10"
```

Ask a natural-language question:

```powershell
curl -X POST http://127.0.0.1:8000/api/ask `
  -H "Content-Type: application/json" `
  -d '{"question":"Show total spending by fiscal year"}'
```

## Testing

```powershell
python -m pytest -q
npm run build --prefix ui
```

The test suite uses mocks where appropriate and does not require production database writes. The application itself is read-only.

## Security Notes

- Never commit `.env`, API keys, database passwords, or tunnel tokens.
- Rotate any credential that has been exposed in terminal history, screenshots, chat, or GitHub.
- Use a read-only SQL login for hosted demonstrations.
- Keep SQL Server port 1433 private.
- The text-to-SQL layer validates generated SQL before execution and limits results to 500 rows.
- The public demo is intended for demonstration, not production hosting.

## Power BI Report

[Open the interactive Power BI report](https://app.powerbi.com/groups/me/reports/7171e917-4de9-4ce7-ac9e-34918540cf3a/7d10024e7d68ae80975d?experience=power-bi)

Power BI access may require the viewer to be signed in and granted permission. The captured visuals in the application and repository provide a viewable fallback.

## Project Status

- [x] SQL Server analytical views
- [x] Power BI report and visual documentation
- [x] Read-only FastAPI API
- [x] Natural-language query desk
- [x] React/Vite UI
- [x] Render deployment configuration
- [x] Free local live demo through a stable ngrok dev domain
- [ ] Permanent hosted database for 24/7 live queries

## License and Data

This project analyzes public data from USAspending.gov. Refer to the source dataset and its terms for authoritative data definitions and usage details.
