-- =============================================================================
-- vw_recipient_spending  |  Recipient × Fiscal Year spending summary
-- =============================================================================
-- Grain   : 1 row per (recipient_id, fiscal_year)
-- Purpose : Answers "Which recipients received the most obligations?" (overall or FY-filtered)
--           and "What percentage is concentrated among top recipients?" (base for concentration view).
-- Intents : recipient_top_spending
-- Features: SUM, COUNT, AVG, RANK() OVER (PARTITION BY fiscal_year), share_of_year
-- Source  : dbo.Transactions JOIN dbo.Recipient
-- =============================================================================

IF OBJECT_ID('dbo.vw_recipient_spending', 'V') IS NOT NULL
    DROP VIEW dbo.vw_recipient_spending;
GO

CREATE VIEW dbo.vw_recipient_spending AS
SELECT
    r.recipient_id,
    r.recipient_name,
    r.recipient_uei,
    r.recipient_parent_name,
    t.fiscal_year,
    SUM(t.federal_action_obligation) AS total_obligations,
    COUNT(*)                          AS transaction_count,
    AVG(t.federal_action_obligation)  AS avg_obligation,
    RANK() OVER (PARTITION BY t.fiscal_year ORDER BY SUM(t.federal_action_obligation) DESC) AS rank_in_year,
    CAST(SUM(t.federal_action_obligation) AS DECIMAL(18,2))
        / NULLIF(SUM(SUM(t.federal_action_obligation)) OVER (PARTITION BY t.fiscal_year), 0) AS share_of_year
FROM dbo.Transactions t
JOIN dbo.Recipient r ON r.recipient_id = t.recipient_id
GROUP BY r.recipient_id, r.recipient_name, r.recipient_uei, r.recipient_parent_name, t.fiscal_year;
GO
