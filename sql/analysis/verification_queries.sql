-- =============================================================================
-- verification_queries.sql  |  Manual verification for AI views & intents
-- =============================================================================
-- Purpose : Run after 001_create_schema.sql + 002_seed.sql + all vw_*.sql.
--           Each block corresponds to a controlled intent / API question.
--           Compare results to the expected values noted in comments.
--           These queries ARE the ground-truth SQL the /ask intents will execute
--           (parameterized by fiscal_year / limit).
-- =============================================================================

USE [USAspendingDB];
GO

PRINT '=== 0. Sanity: row counts and FY totals (must be 8 agencies, 12 recipients, 72 txns) ===';
SELECT 'Agencies' AS tbl, COUNT(*) AS cnt FROM dbo.Agency
UNION ALL SELECT 'Recipients', COUNT(*) FROM dbo.Recipient
UNION ALL SELECT 'Transactions', COUNT(*) FROM dbo.Transactions;
GO

SELECT fiscal_year, COUNT(*) AS txns, SUM(federal_action_obligation) AS total_obligations
FROM dbo.Transactions GROUP BY fiscal_year ORDER BY fiscal_year;
-- Expected (seed): 2023 $8.11B (24 txns), 2024 $9.40B (24), 2025 $11.20B (24)
GO

-- -------------------------------------------------------------------------
-- Q1: Which agencies had the highest spending in a given fiscal year?
-- Intent: agency_top_spending  |  View: vw_agency_spending
-- -------------------------------------------------------------------------
PRINT '=== Q1: Top agencies in FY2025 (DOD must be #1 with $4.55B) ===';
SELECT agency_abbreviation, agency_name, total_obligations, rank_in_year, share_of_year
FROM dbo.vw_agency_spending
WHERE fiscal_year = 2025
ORDER BY rank_in_year;
-- Expected top: DOD $4.55B, HHS $1.73B, DOE $1.15B ...

PRINT '=== Q1b: Top agencies in FY2023 ===';
SELECT agency_abbreviation, total_obligations, rank_in_year
FROM dbo.vw_agency_spending WHERE fiscal_year = 2023 ORDER BY rank_in_year;
GO

-- -------------------------------------------------------------------------
-- Q2: Which agencies increased spending the most year-over-year?
-- Intent: agency_yoy_growth  |  View: vw_agency_yoy_growth
-- Filter: growth_rate DESC, fiscal_year = @year (e.g., 2025 means 2024->2025)
-- -------------------------------------------------------------------------
PRINT '=== Q2: Largest YoY growth 2024->2025 (HHS +31% must be #1) ===';
SELECT agency_abbreviation, fiscal_year, prev_fiscal_year,
       prev_year_obligations, total_obligations, growth_abs, growth_rate, rank_growth_desc
FROM dbo.vw_agency_yoy_growth
WHERE fiscal_year = 2025 AND prev_year_obligations IS NOT NULL
ORDER BY rank_growth_desc;
-- Expected: HHS 0.3106 (~31%), then GSA/DHS/NASA; VA at bottom (negative)

PRINT '=== Q2b: Largest YoY growth 2023->2024 ===';
SELECT agency_abbreviation, growth_rate, rank_growth_desc
FROM dbo.vw_agency_yoy_growth WHERE fiscal_year=2024 ORDER BY rank_growth_desc;
GO

-- -------------------------------------------------------------------------
-- Q3: Which recipients received the most obligations?
-- Intent: recipient_top_spending  |  View: vw_recipient_spending
-- -------------------------------------------------------------------------
PRINT '=== Q3: Top recipients FY2025 (Lockheed ~$1.85B must be #1) ===';
SELECT recipient_name, total_obligations, rank_in_year, share_of_year
FROM dbo.vw_recipient_spending
WHERE fiscal_year = 2025
ORDER BY rank_in_year;
-- Expected: Lockheed > Boeing/Raytheon > HHS-related recipients

PRINT '=== Q3b: Top recipients all-time (no FY filter) ===';
SELECT recipient_name, SUM(total_obligations) AS all_time_total
FROM dbo.vw_recipient_spending
GROUP BY recipient_name
ORDER BY all_time_total DESC;
GO

-- -------------------------------------------------------------------------
-- Q4: What are the largest transactions?
-- Intent: largest_transactions  |  View: vw_largest_transactions
-- -------------------------------------------------------------------------
PRINT '=== Q4: 10 largest transactions overall (DOD-2025-001 $1.85B must be #1) ===';
SELECT TOP 10 award_id, agency_abbreviation, recipient_name, federal_action_obligation, fiscal_year, rank_overall
FROM dbo.vw_largest_transactions
ORDER BY rank_overall;

PRINT '=== Q4b: Largest transactions in FY2024 ===';
SELECT TOP 5 award_id, recipient_name, federal_action_obligation, rn_in_year
FROM dbo.vw_largest_transactions
WHERE fiscal_year = 2024
ORDER BY rn_in_year;
GO

-- -------------------------------------------------------------------------
-- Q5: Which NAICS categories had the highest spending?
-- Intent: naics_top_spending  |  View: vw_spending_by_naics
-- -------------------------------------------------------------------------
PRINT '=== Q5: Top NAICS FY2025 (336411 Aircraft Mfg must dominate) ===';
SELECT naics_code, naics_description, total_obligations, share_of_year, rank_in_year
FROM dbo.vw_spending_by_naics
WHERE fiscal_year = 2025
ORDER BY rank_in_year;

PRINT '=== Q5b: NAICS trend for 541512 (Computer Systems Design) ===';
SELECT fiscal_year, total_obligations, rank_in_year FROM dbo.vw_spending_by_naics WHERE naics_code='541512' ORDER BY fiscal_year;
GO

-- -------------------------------------------------------------------------
-- Q6: How has federal spending changed over time?
-- Intent: spending_trend  |  View: vw_spending_by_fiscal_year
-- -------------------------------------------------------------------------
PRINT '=== Q6: Spending trend (totals must rise: 8.11 -> 9.40 (+15.9%) -> 11.20 (+19.1%)) ===';
SELECT fiscal_year, total_obligations, prev_year_obligations, growth_abs, growth_rate, growth_direction, transaction_count
FROM dbo.vw_spending_by_fiscal_year
ORDER BY fiscal_year;
GO

-- -------------------------------------------------------------------------
-- Q7: Which agencies experienced the largest spending decline?
-- Intent: agency_yoy_decline (same view as Q2, ASC sort)  |  View: vw_agency_yoy_growth
-- -------------------------------------------------------------------------
PRINT '=== Q7: Largest decline 2024->2025 (VA ~-15% must be last) ===';
SELECT agency_abbreviation, fiscal_year, total_obligations, prev_year_obligations, growth_rate, rank_growth_asc
FROM dbo.vw_agency_yoy_growth
WHERE fiscal_year = 2025 AND prev_year_obligations IS NOT NULL
ORDER BY rank_growth_asc;
-- VA should appear top when sorted ASC (most negative)
GO

-- -------------------------------------------------------------------------
-- Q8: What states/locations had the highest spending?
-- Intent: geographic_spending  |  View: vw_geographic_spending
-- -------------------------------------------------------------------------
PRINT '=== Q8: Top states FY2025 (TX/VA/MD should lead) ===';
SELECT recipient_state, total_obligations, share_of_year, rank_in_year, distinct_recipients
FROM dbo.vw_geographic_spending
WHERE fiscal_year = 2025
ORDER BY rank_in_year;

PRINT '=== Q8b: Geographic trend for TX ===';
SELECT fiscal_year, total_obligations, rank_in_year FROM dbo.vw_geographic_spending WHERE recipient_state='TX' ORDER BY fiscal_year;
GO

-- -------------------------------------------------------------------------
-- Q9: What percentage of spending is concentrated among top recipients?
-- Intent: spending_concentration  |  View: vw_spending_concentration
-- -------------------------------------------------------------------------
PRINT '=== Q9: Concentration per FY (Top-1 ~16-17%, Top-5 ~40-45%) ===';
SELECT fiscal_year, total_obligations,
       top1_obligations, top1_share,
       top5_obligations, top5_share,
       top10_obligations, top10_share,
       distinct_recipients
FROM dbo.vw_spending_concentration
ORDER BY fiscal_year;
GO

-- -------------------------------------------------------------------------
-- Extra: End-to-end parameterized examples (what FastAPI will execute)
-- These are the exact parameterized patterns with @fy / @limit.
-- -------------------------------------------------------------------------
PRINT '=== Parameterized example: agency_top_spending @fy=2025, @limit=5 ===';
DECLARE @fy INT = 2025, @limit INT = 5;
SELECT TOP (@limit) agency_abbreviation, agency_name, total_obligations, rank_in_year, share_of_year
FROM dbo.vw_agency_spending WHERE fiscal_year = @fy ORDER BY rank_in_year;
GO

PRINT '=== Parameterized example: largest_transactions @fy=2025, @limit=3 ===';
DECLARE @fy2 INT = 2025, @limit2 INT = 3;
SELECT TOP (@limit2) award_id, recipient_name, federal_action_obligation
FROM dbo.vw_largest_transactions WHERE fiscal_year = @fy2 ORDER BY rn_in_year;
GO

PRINT '=== All verification queries complete. If no errors above, AI views are correct. ===';
GO
