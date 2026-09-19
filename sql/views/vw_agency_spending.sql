-- =============================================================================
-- vw_agency_spending  |  Agency × Fiscal Year spending summary
-- =============================================================================
-- Grain   : 1 row per (awarding_agency_id, fiscal_year)
-- Purpose : Answers "Which agencies had the highest spending in FY X?" and
--           powers Power BI bar/treemap. All totals are SUM(federal_action_obligation).
--           Rankings are computed in SQL so LLM never calculates.
-- Intents : agency_top_spending, agency_ranking
-- Features: SUM, COUNT, AVG, RANK() OVER (PARTITION BY fiscal_year)
-- Source  : dbo.Transactions JOIN dbo.Agency
-- Example : SELECT * FROM vw_agency_spending WHERE fiscal_year=2025 ORDER BY rank_in_year;
-- =============================================================================

IF OBJECT_ID('dbo.vw_agency_spending', 'V') IS NOT NULL
    DROP VIEW dbo.vw_agency_spending;
GO

CREATE VIEW dbo.vw_agency_spending AS
SELECT
    a.agency_id,
    a.agency_name,
    a.agency_abbreviation,
    a.department_name,
    t.fiscal_year,
    SUM(t.federal_action_obligation)  AS total_obligations,
    COUNT(*)                           AS transaction_count,
    AVG(t.federal_action_obligation)   AS avg_obligation,
    MIN(t.action_date)                 AS first_action_date,
    MAX(t.action_date)                 AS last_action_date,
    RANK() OVER (PARTITION BY t.fiscal_year ORDER BY SUM(t.federal_action_obligation) DESC) AS rank_in_year,
    -- Share of FY total (0..1) — denominator via window SUM
    CAST(SUM(t.federal_action_obligation) AS DECIMAL(18,2))
        / NULLIF(SUM(SUM(t.federal_action_obligation)) OVER (PARTITION BY t.fiscal_year), 0) AS share_of_year
FROM dbo.Transactions t
JOIN dbo.Agency a ON a.agency_id = t.awarding_agency_id
GROUP BY
    a.agency_id, a.agency_name, a.agency_abbreviation, a.department_name, t.fiscal_year;
GO
