-- =============================================================================
-- vw_spending_concentration  |  Concentration of spending among top recipients
-- =============================================================================
-- Grain   : 1 row per fiscal_year
-- Purpose : Answers "What percentage of spending is concentrated among the top
--           recipients?" — reports Top-1 / Top-5 / Top-10 shares per FY.
--           Uses deterministic recipient ranking per FY.
-- Intents : spending_concentration
-- Features: CTEs, RANK(), SUM() OVER, SUM(CASE WHEN rank <= N), NULLIF()
-- =============================================================================

IF OBJECT_ID('dbo.vw_spending_concentration', 'V') IS NOT NULL
    DROP VIEW dbo.vw_spending_concentration;
GO

CREATE VIEW dbo.vw_spending_concentration AS
WITH recipient_year AS (
    SELECT
        t.fiscal_year,
        t.recipient_id,
        SUM(t.federal_action_obligation) AS total_obligations
    FROM dbo.Transactions t
    GROUP BY t.fiscal_year, t.recipient_id
),
ranked AS (
    SELECT
        fiscal_year,
        recipient_id,
        total_obligations,
        RANK() OVER (PARTITION BY fiscal_year ORDER BY total_obligations DESC) AS rnk
    FROM recipient_year
),
fy_total AS (
    SELECT fiscal_year, SUM(total_obligations) AS fy_total_obligations
    FROM recipient_year
    GROUP BY fiscal_year
)
SELECT
    f.fiscal_year,
    f.fy_total_obligations AS total_obligations,
    -- Top-N sums
    (SELECT SUM(total_obligations) FROM ranked r WHERE r.fiscal_year = f.fiscal_year AND r.rnk = 1)  AS top1_obligations,
    (SELECT SUM(total_obligations) FROM ranked r WHERE r.fiscal_year = f.fiscal_year AND r.rnk <= 5)  AS top5_obligations,
    (SELECT SUM(total_obligations) FROM ranked r WHERE r.fiscal_year = f.fiscal_year AND r.rnk <= 10) AS top10_obligations,
    -- Shares (0..1)
    CAST((SELECT SUM(total_obligations) FROM ranked r WHERE r.fiscal_year = f.fiscal_year AND r.rnk = 1)  AS DECIMAL(18,2)) / NULLIF(f.fy_total_obligations, 0) AS top1_share,
    CAST((SELECT SUM(total_obligations) FROM ranked r WHERE r.fiscal_year = f.fiscal_year AND r.rnk <= 5)  AS DECIMAL(18,2)) / NULLIF(f.fy_total_obligations, 0) AS top5_share,
    CAST((SELECT SUM(total_obligations) FROM ranked r WHERE r.fiscal_year = f.fiscal_year AND r.rnk <= 10) AS DECIMAL(18,2)) / NULLIF(f.fy_total_obligations, 0) AS top10_share,
    (SELECT COUNT(*) FROM ranked r WHERE r.fiscal_year = f.fiscal_year) AS distinct_recipients,
    (SELECT COUNT(*) FROM ranked r WHERE r.fiscal_year = f.fiscal_year AND r.rnk <= 5) AS top5_recipient_count
FROM fy_total f;
GO
