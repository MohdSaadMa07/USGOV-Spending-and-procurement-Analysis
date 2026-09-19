-- =============================================================================
-- vw_agency_yoy_growth  |  Agency year-over-year growth (deterministic)
-- =============================================================================
-- Grain   : 1 row per (awarding_agency_id, fiscal_year) where fiscal_year >= min FY
-- Purpose : Answers:
--           - "Which agencies increased spending the most year-over-year?"
--           - "Which agencies experienced the largest spending decline?"
--           All growth math is in SQL via LAG(); LLM only explains.
-- Intents : agency_yoy_growth, agency_yoy_decline
-- Features: CTE, LAG() OVER (PARTITION BY agency ORDER BY fiscal_year),
--           NULLIF(), CASE, RANK()
-- Source  : dbo.vw_agency_spending logic inlined (no view-on-view dependency for portability)
-- Note    : First FY per agency has NULL prev values and is excluded from ranked growth.
-- =============================================================================

IF OBJECT_ID('dbo.vw_agency_yoy_growth', 'V') IS NOT NULL
    DROP VIEW dbo.vw_agency_yoy_growth;
GO

CREATE VIEW dbo.vw_agency_yoy_growth AS
WITH agency_year AS (
    SELECT
        a.agency_id,
        a.agency_name,
        a.agency_abbreviation,
        a.department_name,
        t.fiscal_year,
        SUM(t.federal_action_obligation) AS total_obligations,
        COUNT(*)                          AS transaction_count
    FROM dbo.Transactions t
    JOIN dbo.Agency a ON a.agency_id = t.awarding_agency_id
    GROUP BY a.agency_id, a.agency_name, a.agency_abbreviation, a.department_name, t.fiscal_year
),
with_lag AS (
    SELECT
        *,
        LAG(total_obligations) OVER (PARTITION BY agency_id ORDER BY fiscal_year) AS prev_year_obligations,
        LAG(fiscal_year)       OVER (PARTITION BY agency_id ORDER BY fiscal_year) AS prev_fiscal_year
    FROM agency_year
)
SELECT
    agency_id,
    agency_name,
    agency_abbreviation,
    department_name,
    fiscal_year,
    prev_fiscal_year,
    total_obligations,
    prev_year_obligations,
    -- Absolute growth
    total_obligations - prev_year_obligations AS growth_abs,
    -- Rate: NULL when prev is 0 or NULL (first year)
    CASE
        WHEN prev_year_obligations IS NULL THEN NULL
        ELSE (total_obligations - prev_year_obligations) / NULLIF(prev_year_obligations, 0)
    END AS growth_rate,
    -- Human-readable growth pct string helper not stored; LLM formats
    CASE
        WHEN prev_year_obligations IS NULL THEN NULL
        WHEN prev_year_obligations = 0 THEN NULL
        WHEN total_obligations > prev_year_obligations THEN 'increase'
        WHEN total_obligations < prev_year_obligations THEN 'decrease'
        ELSE 'flat'
    END AS growth_direction,
    RANK() OVER (PARTITION BY fiscal_year ORDER BY (total_obligations - prev_year_obligations) / NULLIF(prev_year_obligations, 0) DESC) AS rank_growth_desc,
    RANK() OVER (PARTITION BY fiscal_year ORDER BY (total_obligations - prev_year_obligations) / NULLIF(prev_year_obligations, 0) ASC)  AS rank_growth_asc
FROM with_lag;
GO
