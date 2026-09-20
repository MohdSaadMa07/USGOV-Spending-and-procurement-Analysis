# US Government Spending & Procurement Analysis

An interactive analytics project built from public federal spending data from [USAspending.gov](https://www.usaspending.gov/).

## Live Demo

[Open the live application](https://gopher-wielder-banter.ngrok-free.dev/ui/)

> The demo runs from a local machine through a free ngrok tunnel. The computer, SQL Server, FastAPI, and ngrok must be running for the link to work.

## Project Highlights

- Analyze U.S. government spending and procurement activity.
- Ask natural-language questions about federal spending.
- View validated, read-only SQL results.
- Explore Power BI-inspired report visuals.
- Compare agencies, recipients, fiscal years, award types, and spending concentration.

## Application

### Query Desk

Ask questions such as:

- Show total spending by fiscal year.
- Which agencies have the highest obligations?
- What percentage is concentrated among the top ten recipients?

### Power BI Visuals

The visual gallery includes:

- Total federal obligations
- Top-10 recipient concentration
- Unique vendors
- Top recipients
- Fiscal-year spending trends
- Period-over-period changes
- Award-type breakdowns

## Screenshots

### Power BI Report

![Power BI report](ui/public/MAIN%20HEADER%20IMAGE.png)

| Visual | Preview |
| --- | --- |
| Total obligations | [Open image](ui/public/01-total-obligations.png) |
| Top-10 concentration | [Open image](ui/public/02-top10-concentration.png) |
| Unique vendors | [Open image](ui/public/03-unique-vendors.png) |
| Top recipients | [Open image](ui/public/06-top-recipients-table.png) |
| Fiscal-year trend | [Open image](ui/public/05-fiscal-year-trend.png) |
| Award types | [Open image](ui/public/08-award-type.png) |

> Add a Query Desk screenshot at `ui/public/query-desk.png` when available.

## Technology

- **Frontend:** React, Vite, JavaScript
- **Backend:** FastAPI, Python
- **Database:** Microsoft SQL Server
- **Analytics:** Power BI
- **AI layer:** Groq natural-language-to-SQL
- **Deployment/demo:** Render configuration and ngrok tunnel

## Run Locally

### Requirements

- Python 3.10+
- Node.js and npm
- SQL Server with the project database
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

For text-to-SQL, add your own Groq key to `.env`. Never commit `.env` or API keys.

## API

- `/ui/` - web application
- `/docs` - interactive API documentation
- `/health` - service and database health check
- `/api/agency-spending` - agency spending data
- `/api/ask` - natural-language analytics queries

## Power BI Report

[Open the interactive Power BI report](https://app.powerbi.com/groups/me/reports/7171e917-4de9-4ce7-ac9e-34918540cf3a/7d10024e7d68ae80975d?experience=power-bi)

Power BI access may require permission. The captured visuals above provide a viewable alternative.

## Security

- The application is read-only.
- Generated queries are validated before execution.
- SQL Server port 1433 is not exposed through the demo.
- Credentials and API keys are stored locally or in hosting environment variables.

## Data

This project uses public U.S. government spending data from USAspending.gov.
