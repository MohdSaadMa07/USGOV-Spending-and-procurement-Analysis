-- =============================================================================
-- vw_recipient_yoy_growth  |  Recipient year-over-year growth
-- =============================================================================
-- Grain   : 1 row per (recipient_id, fiscal_year)
-- Purpose : Supports recipient-level YoY narratives and future /insights.
--           Mirrors vw_agency_yoy_growth pattern for consistency.
-- Intents : recipient_yoy_growth (optional /insights drill-down)
-- Features: CTE, LAG() OVER (PARTITION BY recipient), NULLIF(), CASE, RANK()
-- =============================================================================

IF OBJECT_ID('dbo.vw_recipient_yoy_growth', 'V') IS NOT NULL
    DROP VIEW dbo.vw_recipient_yoy_growth;
GO

CREATE VIEW dbo.vw_recipient_yoy_growth AS
WITH recipient_year AS (
    SELECT
        r.recipient_id,
        r.recipient_name,
        r.recipient_uei,
        r.recipient_parent_name,
        t.fiscal_year,
        SUM(t.federal_action_obligation) AS total_obligations,
        COUNT(*)                          AS transaction_count
    FROM dbo.Transactions t
    JOIN dbo.Recipient r ON r.recipient_id = t.recipient_id
    GROUP BY r.recipient_id, r.recipient_name, r.recipient_uei, r.recipient_parent_name, t.fiscal_year
),
with_lag AS (
    SELECT
        *,
        LAG(total_obligations) OVER (PARTITION BY recipient_id ORDER BY fiscal_year) AS prev_year_obligations,
        LAG(fiscal_year)       OVER (PARTITION BY recipient_id ORDER BY fiscal_year) AS prev_fiscal_year
    FROM recipient_year
)
SELECT
    recipient_id,
    recipient_name,
    recipient_uei,
    recipient_parent_name,
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
    RANK() OVER (PARTITION BY fiscal_year ORDER BY (total_obligations - prev_year_obligations) / NULLIF(prev_year_obligations, 0) DESC) AS rank_growth_desc
FROM with_lag;
GO
