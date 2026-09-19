-- =============================================================================
-- vw_spending_by_naics  |  Spending by NAICS category × fiscal year
-- =============================================================================
-- Grain   : 1 row per (naics_code, fiscal_year)
-- Purpose : Answers "Which NAICS categories had the highest spending?"
--           Includes share of FY total so LLM can say "X% of FY2025 obligations".
-- Intents : naics_top_spending
-- Features: SUM, COUNT, AVG, RANK() OVER (PARTITION BY fiscal_year), window share
-- Note    : NULL naics_code grouped as 'UNKNOWN' for completeness.
-- =============================================================================

IF OBJECT_ID('dbo.vw_spending_by_naics', 'V') IS NOT NULL
    DROP VIEW dbo.vw_spending_by_naics;
GO

CREATE VIEW dbo.vw_spending_by_naics AS
SELECT
    COALESCE(t.naics_code, 'UNKNOWN')        AS naics_code,
    COALESCE(t.naics_description, 'Unknown') AS naics_description,
    t.fiscal_year,
    SUM(t.federal_action_obligation) AS total_obligations,
    COUNT(*)                          AS transaction_count,
    AVG(t.federal_action_obligation)  AS avg_obligation,
    RANK() OVER (PARTITION BY t.fiscal_year ORDER BY SUM(t.federal_action_obligation) DESC) AS rank_in_year,
    CAST(SUM(t.federal_action_obligation) AS DECIMAL(18,2))
        / NULLIF(SUM(SUM(t.federal_action_obligation)) OVER (PARTITION BY t.fiscal_year), 0) AS share_of_year
FROM dbo.Transactions t
GROUP BY COALESCE(t.naics_code, 'UNKNOWN'), COALESCE(t.naics_description, 'Unknown'), t.fiscal_year;
GO
