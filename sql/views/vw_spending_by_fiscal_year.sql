-- =============================================================================
-- vw_spending_by_fiscal_year  |  Federal spending trend over time
-- =============================================================================
-- Grain   : 1 row per fiscal_year
-- Purpose : Answers "How has federal spending changed over time?"
--           Provides FY totals, transaction counts, average obligation,
--           and deterministic YoY growth for the entire federal portfolio.
-- Intents : spending_trend, spending_over_time
-- Features: SUM, COUNT, AVG, CTE, LAG(), NULLIF(), CASE
-- =============================================================================

IF OBJECT_ID('dbo.vw_spending_by_fiscal_year', 'V') IS NOT NULL
    DROP VIEW dbo.vw_spending_by_fiscal_year;
GO

CREATE VIEW dbo.vw_spending_by_fiscal_year AS
WITH fy AS (
    SELECT
        fiscal_year,
        SUM(federal_action_obligation) AS total_obligations,
        COUNT(*)                        AS transaction_count,
        AVG(federal_action_obligation)  AS avg_obligation,
        MIN(action_date)                AS first_action_date,
        MAX(action_date)                AS last_action_date
    FROM dbo.Transactions
    GROUP BY fiscal_year
),
with_lag AS (
    SELECT
        *,
        LAG(total_obligations) OVER (ORDER BY fiscal_year) AS prev_year_obligations,
        LAG(fiscal_year)       OVER (ORDER BY fiscal_year) AS prev_fiscal_year
    FROM fy
)
SELECT
    fiscal_year,
    prev_fiscal_year,
    total_obligations,
    prev_year_obligations,
    total_obligations - prev_year_obligations AS growth_abs,
    CASE
        WHEN prev_year_obligations IS NULL THEN NULL
        ELSE (total_obligations - prev_year_obligations) / NULLIF(prev_year_obligations, 0)
    END AS growth_rate,
    CASE
        WHEN prev_year_obligations IS NULL THEN NULL
        WHEN total_obligations > prev_year_obligations THEN 'increase'
        WHEN total_obligations < prev_year_obligations THEN 'decrease'
        ELSE 'flat'
    END AS growth_direction,
    transaction_count,
    avg_obligation,
    first_action_date,
    last_action_date
FROM with_lag;
GO
