-- =============================================================================
-- vw_largest_transactions  |  Ranked individual transactions
-- =============================================================================
-- Grain   : 1 row per transaction (same as dbo.Transactions) but enriched
-- Purpose : Answers "What are the largest transactions/contracts?"
--           Deterministic ranking per FY and overall via ROW_NUMBER/RANK.
-- Intents : largest_transactions
-- Features: ROW_NUMBER() OVER (PARTITION BY fiscal_year ORDER BY obligation DESC),
--           RANK() OVER (ORDER BY obligation DESC), JOINs for display names
-- Limit   : API will apply TOP/@limit (default 10, max 500) — view itself is unfiltered
-- =============================================================================

IF OBJECT_ID('dbo.vw_largest_transactions', 'V') IS NOT NULL
    DROP VIEW dbo.vw_largest_transactions;
GO

CREATE VIEW dbo.vw_largest_transactions AS
SELECT
    t.transaction_id,
    t.award_id,
    t.modification_number,
    t.fiscal_year,
    t.action_date,
    a.agency_name,
    a.agency_abbreviation,
    r.recipient_name,
    r.recipient_uei,
    t.naics_code,
    t.naics_description,
    t.product_or_service_code,
    t.recipient_state,
    t.recipient_city,
    t.pop_state,
    t.federal_action_obligation,
    t.total_dollars_obligated,
    t.award_type,
    t.contract_award_type,
    ROW_NUMBER() OVER (PARTITION BY t.fiscal_year ORDER BY t.federal_action_obligation DESC, t.transaction_id) AS rn_in_year,
    RANK()       OVER (PARTITION BY t.fiscal_year ORDER BY t.federal_action_obligation DESC) AS rank_in_year,
    ROW_NUMBER() OVER (ORDER BY t.federal_action_obligation DESC, t.transaction_id)          AS rn_overall,
    RANK()       OVER (ORDER BY t.federal_action_obligation DESC)                            AS rank_overall
FROM dbo.Transactions t
JOIN dbo.Agency a    ON a.agency_id = t.awarding_agency_id
JOIN dbo.Recipient r ON r.recipient_id = t.recipient_id;
GO
