# AI-Ready Analytical Views

> All views are deterministic. YoY, ranks, shares, and rates are computed in SQL. LLM only explains.
> Anomaly view deferred per MVP scope (Phase 1 excludes anomaly detection).

## Overview

| View | Grain | Purpose / Question | Intent | SQL Features |
|------|-------|--------------------|--------|--------------|
| `vw_agency_spending` | agency × FY | Which agencies had highest spending in FY X? | `agency_top_spending` | `SUM, COUNT, AVG, RANK() OVER (PARTITION BY FY)` |
| `vw_agency_yoy_growth` | agency × FY | Which agencies increased/decreased most YoY? | `agency_yoy_growth`, `agency_yoy_decline` | `CTE, LAG(), NULLIF(), CASE, RANK()` |
| `vw_recipient_spending` | recipient × FY | Which recipients received most obligations? | `recipient_top_spending` | `SUM, RANK(), share_of_year` |
| `vw_recipient_yoy_growth` | recipient × FY | Recipient YoY drill-down for /insights | `recipient_yoy_growth` | `CTE, LAG(), RANK()` |
| `vw_spending_by_fiscal_year` | FY | How has federal spending changed over time? | `spending_trend` | `CTE, LAG(), NULLIF()` |
| `vw_spending_by_naics` | NAICS × FY | Which NAICS categories had highest spending? | `naics_top_spending` | `SUM, RANK(), window share` |
| `vw_geographic_spending` | state × FY | Which states/locations had highest spending? | `geographic_spending` | `COUNT(DISTINCT), RANK(), share` |
| `vw_largest_transactions` | transaction | What are the largest transactions/contracts? | `largest_transactions` | `ROW_NUMBER(), RANK() OVER` |
| `vw_spending_concentration` | FY | What % is concentrated among top recipients? | `spending_concentration` | `CTEs, RANK(), subquery SUM, NULLIF()` |

## Execution

```powershell
# 1. Create schema + seed (once)
sqlcmd -S $env:SQL_SERVER -d master -i sql/setup/001_create_schema.sql
sqlcmd -S $env:SQL_SERVER -d USAspendingDB -i sql/setup/002_seed.sql

# 2. Create views (idempotent, any order)
Get-ChildItem sql/views/*.sql | ForEach-Object { sqlcmd -S $env:SQL_SERVER -d USAspendingDB -i $_.FullName }

# 3. Verify
sqlcmd -S $env:SQL_SERVER -d USAspendingDB -i sql/analysis/verification_queries.sql
```

## Design Notes

- Views use `DROP VIEW IF EXISTS` + `CREATE VIEW` — re-runnable.
- No `SELECT *` — explicit columns for Power BI import stability.
- Money: `DECIMAL(18,2)` throughout; presentation formatting (`FORMAT(...,'C0')`) only in verification queries, never in views.
- First-FY rows have `prev_year_obligations = NULL` and are excluded from growth ranking via `WHERE prev_year_obligations IS NOT NULL` in the API.
- `share_of_year` = `SUM(fact) / SUM(SUM(fact)) OVER (PARTITION BY fiscal_year)` — avoids extra join.
- All parameterized API queries apply `WHERE fiscal_year = @fy` + `TOP (@limit)` + `ORDER BY rank` — never concatenate user input.
