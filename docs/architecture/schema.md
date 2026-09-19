# Canonical Schema — USAspendingDB (SQL Server)

> Source of truth: **SQL Server**. All facts calculated in SQL. LLM only explains results.
> Grain, column names, and metric definitions are fixed here so that Python, SQL views, and Power BI stay consistent.

## 1. Design Decisions

| Decision | Value | Rationale |
|----------|-------|-----------|
| **Database** | `USAspendingDB` (`SQL_DATABASE` env) | Matches `.env.example`; Power BI connects via `SQL_SERVER`/`SQL_DATABASE` |
| **Fiscal year field** | `dbo.Transactions.fiscal_year INT` | Derived from `action_date` FY. USAspending `action_date_fiscal_year`. INT for partitioning/sorting |
| **Primary spending metric** | `federal_action_obligation DECIMAL(18,2)` | USAspending `federal_action_obligation` — signed obligation per action. Single source for all aggregations |
| **Secondary metric** | `total_dollars_obligated DECIMAL(18,2)` | Kept for award-level rollups, not used in FY views |
| **Grain** | 1 row = 1 contract award modification/action | `(award_id, modification_number)` is natural key. Prevents double-counting divisions/awards. Use `SUM(federal_action_obligation)` to roll up to award/FY |
| **Agency model** | Normalized `dbo.Agency` FK'd from `awarding_agency_id` + `funding_agency_id` | Enables agency × FY analytics without string dedup; keeps Power BI dimension clean |
| **Recipient model** | Normalized `dbo.Recipient` | Same reason; UEI kept for future joins |
| **NAICS** | Denormalized on fact (`naics_code`, `naics_description`) | NAICS rarely needs its own dimension for MVP; 6-digit code is join key |
| **Geography** | Denormalized on fact (`recipient_state`, `pop_state`, `recipient_city`) | USAspending provides both recipient & POP location; recipient_state is the MVP rollup |
| **Idempotency** | All DDL uses `IF NOT EXISTS` / `DROP VIEW IF EXISTS` | Re-runnable on local/dev SQL Server without manual cleanup |

## 2. Tables

### dbo.Agency
| Column | Type | Notes |
|--------|------|-------|
| `agency_id` | `INT IDENTITY(1,1) PK` | Surrogate |
| `agency_name` | `NVARCHAR(255) NOT NULL` | e.g. `Department of Defense` |
| `agency_abbreviation` | `NVARCHAR(20)` | e.g. `DOD` |
| `department_name` | `NVARCHAR(255)` | Parent dept for rollups |
| `agency_type` | `NVARCHAR(50)` | `awarding` / `funding` / `both` |

Seed: 8 agencies covering DOD, HHS, DOE, DHS, NASA, DOT, VA, GSA — enough to demo concentration vs. YoY.

### dbo.Recipient
| Column | Type | Notes |
|--------|------|-------|
| `recipient_id` | `INT IDENTITY PK` | Surrogate |
| `recipient_name` | `NVARCHAR(255) NOT NULL` | Legal entity |
| `recipient_uei` | `NVARCHAR(20)` | SAM UEI |
| `recipient_parent_name` | `NVARCHAR(255)` | Ultimate parent |

Seed: 12 recipients (Lockheed Martin, Boeing, Raytheon, etc. + 4 small businesses) to create realistic concentration (top 3 ≈ 45% of FY).

### dbo.Transactions (FACT)
| Column | Type | Constraint | Notes |
|--------|------|------------|-------|
| `transaction_id` | `BIGINT IDENTITY PK` | | Surrogate |
| `award_id` | `NVARCHAR(50) NOT NULL` | | PIID/FAIN; part of natural key |
| `modification_number` | `NVARCHAR(20) NOT NULL` | `DF_Transactions_modification_number DEFAULT '0'` | Natural key; `0` = base award |
| `fiscal_year` | `INT NOT NULL` | `CHK fiscal_year BETWEEN 2000 AND 2100` | FY of `action_date` |
| `action_date` | `DATE NOT NULL` | | Obligation date |
| `awarding_agency_id` | `INT NOT NULL` | `FK → Agency` | Who awarded |
| `funding_agency_id` | `INT` | `FK → Agency` | Who funded (nullable for MVP) |
| `recipient_id` | `INT NOT NULL` | `FK → Recipient` | Who received |
| `naics_code` | `NVARCHAR(6)` | | 6-digit NAICS |
| `naics_description` | `NVARCHAR(255)` | | |
| `product_or_service_code` | `NVARCHAR(10)` | | PSC |
| `recipient_state` | `NVARCHAR(2)` | | 2-letter code |
| `recipient_city` | `NVARCHAR(100)` | | |
| `pop_state` | `NVARCHAR(2)` | | Place of performance |
| `federal_action_obligation` | `DECIMAL(18,2) NOT NULL` | `DF 0` | **Primary metric**. Signed. |
| `total_dollars_obligated` | `DECIMAL(18,2)` | | |
| `award_type` | `NVARCHAR(50)` | | `Contract`, `Grant`, … |
| `contract_award_type` | `NVARCHAR(50)` | | `Definitive Contract`, … |
| `created_at` | `DATETIME2` | `DEFAULT SYSUTCDATETIME()` | Audit |

**Natural key:** `UNIQUE(award_id, modification_number)`  
**Indexes:**
- `IX_Transactions_FY (fiscal_year)`
- `IX_Transactions_AgencyFY (awarding_agency_id, fiscal_year) INCLUDE (federal_action_obligation)`
- `IX_Transactions_Recipient (recipient_id)`
- `IX_Transactions_NAICS (naics_code)`
- `IX_Transactions_State (recipient_state, fiscal_year)`

Seed: ~72 rows across FY2023–2025, intentionally crafted so:
- FY totals increase YoY (2023: ~$8.1B, 2024: ~$9.4B, 2025: ~$11.2B)
- DOD is largest agency every FY; HHS shows largest YoY % jump 2024→2025 (+31% in seed)
- VA shows YoY decline (to exercise "largest decline" intent)
- Top-3 recipients concentration is stable (~44–47%) for `vw_spending_concentration` tests

## 3. Metric Definitions (all in SQL, never LLM)

| Metric | SQL Expression | View |
|--------|---------------|------|
| `total_obligations` | `SUM(federal_action_obligation)` | All `*_spending` views |
| `prev_year_obligations` | `LAG(total_obligations) OVER (PARTITION BY … ORDER BY fiscal_year)` | `*_yoy_growth` |
| `growth_abs` | `total_obligations - prev_year_obligations` | YoY views |
| `growth_rate` | `growth_abs / NULLIF(prev_year_obligations, 0)` | YoY views |
| `rank_in_year` | `RANK() OVER (PARTITION BY fiscal_year ORDER BY total_obligations DESC)` | Ranked views |
| `share_of_year` | `total_obligations / NULLIF(SUM(total_obligations) OVER (PARTITION BY fiscal_year),0)` | NAICS, concentration |
| `transaction_count` | `COUNT(*)` | All spending views |
| `avg_obligation` | `AVG(federal_action_obligation)` | Spending views |

## 4. What Is Out of Scope for MVP

- RAG / embeddings / vector DB
- Text-to-SQL (only controlled intents in Phase 3)
- Anomaly detection / z-score view (`vw_anomaly_metrics` deferred)
- Power BI PBIX (only SQL views that Power BI will import)

## 5. Execution Order

```powershell
sqlcmd -S $env:SQL_SERVER -d master -i sql/setup/001_create_schema.sql
sqlcmd -S $env:SQL_SERVER -d USAspendingDB -i sql/setup/002_seed.sql
# views are idempotent — run in any order, but 002_seed.sql must follow 001
Get-ChildItem sql/views/*.sql | ForEach-Object { sqlcmd -S $env:SQL_SERVER -d USAspendingDB -i $_.FullName }
sqlcmd -S $env:SQL_SERVER -d USAspendingDB -i sql/analysis/verification_queries.sql
```

If SQL Server is not reachable, Python validates syntax: `python -c "import sqlglot; sqlglot.transpile(open('sql/views/vw_...sql').read(), read='tsql')"` (done in Step 6 of todo).
