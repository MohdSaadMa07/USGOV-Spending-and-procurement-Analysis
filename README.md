# US Government Spending & Procurement Analysis

An end-to-end analytics project using public federal spending data from [USAspending.gov](https://www.usaspending.gov/). The project combines SQL Server data preparation, analytical views, Power BI reporting, and a natural-language query interface for exploring procurement patterns.

## Live Demo

[Open the live application](https://gopher-wielder-banter.ngrok-free.dev/ui/)

> The demo runs from a local machine through a free ngrok tunnel. The computer, SQL Server, FastAPI, and ngrok must be running for the link to work.

## Analytical Objective

The goal is to make federal procurement data easier to analyze and explain. The project focuses on:

- How federal obligations change across fiscal years.
- Which agencies and recipients account for the largest obligations.
- How concentrated spending is among the top recipients.
- Which award types drive total spending.
- How spending changes from one period to the next.
- How natural-language questions can be translated into transparent analytical queries.

## Key Metrics

The report is designed around practical procurement KPIs:

- Total federal obligations
- Obligations by fiscal year
- Obligations by agency
- Obligations by recipient
- Top-10 recipient concentration
- Unique vendors or recipients
- Award-type distribution
- Period-over-period spending change

The captured report snapshot represents approximately **$104.65 billion** in obligations, with the top ten recipients accounting for approximately **24.14%** of total obligations and roughly **35,000 unique recipients**.

## Analytical Workflow

```text
Public USAspending data
        |
        v
SQL Server data store
        |
        v
Analytical views and aggregations
        |
        +--> Power BI report and visual analysis
        |
        +--> FastAPI read-only API
                    |
                    v
          Natural-language query desk
```

The workflow separates data preparation from reporting and exploration:

1. Store the public procurement data in SQL Server.
2. Create reusable views for agencies, recipients, fiscal years, award types, and concentration.
3. Use Power BI to communicate trends and comparisons.
4. Expose selected analytical views through a read-only API.
5. Let users ask business questions in plain language and inspect the generated SQL.

## Report Views

### Query Desk

The Query Desk supports questions such as:

- Show total spending by fiscal year.
- Which agencies have the highest total obligations?
- Which recipients receive the most federal obligations?
- Which award types account for the most spending?
- What percentage is concentrated among the top ten recipients?
- How did spending change between fiscal years?

Each answer returns the result rows and generated SQL so the analysis remains inspectable rather than acting as a black box.

### Power BI Visuals

The Power BI analysis includes:

- Total federal obligations KPI
- Top-10 concentration KPI
- Unique vendor KPI
- Top recipients ranked table
- Top recipients comparison chart
- Fiscal-year trend line
- Period-over-period change waterfall
- Award-type composition chart

## Interactive Power BI Report

The deployed application embeds the live Power BI report in its **Power BI
Report** tab. The report replaces screenshot-based presentation in the active
UI while the original image assets remain in the repository for archival use.

Each report visual has a specific analytical purpose: the three KPI cards show
total obligations, top-ten recipient concentration, and unique vendor count;
the recipient table and bar chart show the exact ranking and relative size of
the leading vendors; the fiscal-year line chart shows the long-term trend; the
waterfall explains each period's increase or decrease; and the award-type pie
chart shows which procurement mechanisms make up total obligations. Use Power
BI slicers, tooltips, and the action bar before comparing values across visuals.

## Data Model and Analytical Views

The text-to-SQL layer uses a small set of approved analytical views:

- `vw_AgencySpending` - agencies ranked by total obligations.
- `vw_AwardTypeSpending` - obligations and transaction counts by award type.
- `vw_FederalSpendingByYear` - fiscal-year totals.
- `vw_PeriodSpendingChange` - fiscal-year totals with prior-period change.
- `vw_RecipientSpendingRank` - recipients ranked by obligations.
- `vw_Top10RecipientConcentration` - spending share held by the top ten recipients.

These views turn repeated analytical questions into reusable reporting structures and keep the dashboard logic separate from raw transaction-level data.

## Skills Demonstrated

### Data Analysis

- KPI definition and metric design
- Trend analysis across fiscal years
- Ranking and Pareto-style concentration analysis
- Period-over-period comparison
- Category analysis by award type
- Translating business questions into measurable queries
- Communicating findings through dashboards and visual summaries

### SQL and Data Preparation

- SQL Server and T-SQL
- Aggregations, ranking, grouping, and filtering
- Reusable analytical views
- Parameterized queries
- Read-only data access patterns
- Metadata-driven schema context for query generation

### Data Science and AI Exploration

- Natural-language-to-SQL workflow
- Prompt construction from live analytical schema metadata
- SQL parsing and validation with `sqlglot`
- Guardrails for restricting generated queries to approved views
- Transparent results with generated SQL shown to the user

## Technology

- **Data source:** USAspending.gov
- **Database:** Microsoft SQL Server
- **Analytics and reporting:** Power BI
- **Backend:** Python, FastAPI, pyodbc
- **Query validation:** sqlglot
- **Natural-language layer:** Groq
- **Frontend:** React, Vite, JavaScript

## Run Locally

### Requirements

- Python 3.10+
- Node.js and npm
- SQL Server with the project database and views
- ODBC Driver 17 or 18 for SQL Server

### Setup

```powershell
Copy-Item .env.example .env
pip install -r requirements.txt
npm install --prefix ui
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open the application at:

```text
http://127.0.0.1:8000/ui/
```

For natural-language queries, add your own Groq key to `.env`. Never commit `.env`, API keys, or database credentials.

## API Routes

- `/ui/` - interactive analytics application
- `/docs` - FastAPI documentation
- `/health` - application and database health check
- `/api/agency-spending` - agency spending data with optional fiscal-year filtering
- `/api/ask` - natural-language analytics questions

## Power BI Report

The report is embedded at `/ui/` and uses Power BI's native filters, tooltips,
and action bar. Viewers must have access under the report's Power BI sharing or
embed settings.

## Analytical Safeguards

- The application is read-only.
- Generated SQL is validated before execution.
- Queries are restricted to approved analytical views.
- Results are capped to prevent oversized responses.
- Database errors are sanitized before being returned to users.
- SQL Server port 1433 is not exposed through the public demo.

## Limitations and Next Steps

- The current live demo depends on a local SQL Server and local machine availability.
- The free ngrok URL is stable, but the demo is unavailable when the local services are stopped.
- A production deployment would use a hosted database, managed credentials, and a permanent application host.
- Future analysis could add anomaly detection, agency peer comparisons, geographic analysis, and automated report refreshes.

## Data

This project uses public U.S. government spending data from USAspending.gov. The report is intended for exploratory analysis and portfolio demonstration.
