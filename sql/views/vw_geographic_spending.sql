-- =============================================================================
-- vw_geographic_spending  |  Spending by state (recipient location) × FY
-- =============================================================================
-- Grain   : 1 row per (recipient_state, fiscal_year)
-- Purpose : Answers "What states/locations had the highest spending?"
--           Uses recipient_state (contractor location). pop_state available
--           on fact for future POP view variant.
-- Intents : geographic_spending
-- Features: SUM, COUNT, RANK() OVER (PARTITION BY fiscal_year), share, LAG optional
-- =============================================================================

IF OBJECT_ID('dbo.vw_geographic_spending', 'V') IS NOT NULL
    DROP VIEW dbo.vw_geographic_spending;
GO

CREATE VIEW dbo.vw_geographic_spending AS
SELECT
    COALESCE(t.recipient_state, 'UNKNOWN') AS recipient_state,
    t.fiscal_year,
    SUM(t.federal_action_obligation) AS total_obligations,
    COUNT(*)                          AS transaction_count,
    AVG(t.federal_action_obligation)  AS avg_obligation,
    COUNT(DISTINCT t.recipient_id)    AS distinct_recipients,
    RANK() OVER (PARTITION BY t.fiscal_year ORDER BY SUM(t.federal_action_obligation) DESC) AS rank_in_year,
    CAST(SUM(t.federal_action_obligation) AS DECIMAL(18,2))
        / NULLIF(SUM(SUM(t.federal_action_obligation)) OVER (PARTITION BY t.fiscal_year), 0) AS share_of_year
FROM dbo.Transactions t
GROUP BY COALESCE(t.recipient_state, 'UNKNOWN'), t.fiscal_year;
GO
