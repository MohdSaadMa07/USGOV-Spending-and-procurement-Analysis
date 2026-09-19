import pytest

from app.text2sql.validator import MAX_TOP, validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT TOP 10 Agency FROM dbo.vw_AgencySpending ORDER BY TotalObligations DESC",
        "WITH yearly AS (SELECT FiscalYear, TotalObligations FROM dbo.vw_FederalSpendingByYear) SELECT * FROM yearly",
        "SELECT TOP 5 Agency FROM dbo.vw_AgencySpending UNION SELECT TOP 5 AwardType FROM dbo.vw_AwardTypeSpending",
    ],
)
def test_valid_queries_are_cleaned(sql):
    result = validate_sql(sql)
    assert result.accepted
    assert result.cleaned_sql
    assert "TOP 500" in result.cleaned_sql or "TOP 10" in result.cleaned_sql or "TOP 5" in result.cleaned_sql


def test_missing_top_gets_safe_cap():
    result = validate_sql("SELECT Agency FROM dbo.vw_AgencySpending")
    assert result.accepted
    assert f"TOP {MAX_TOP}" in result.cleaned_sql


def test_large_top_is_capped():
    result = validate_sql("SELECT TOP 9999 * FROM dbo.vw_AgencySpending")
    assert result.accepted
    assert f"TOP {MAX_TOP}" in result.cleaned_sql


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE dbo.vw_AgencySpending",
        "UPDATE dbo.vw_AgencySpending SET Agency = 'x'",
        "SELECT * FROM dbo.vw_AgencySpending; DROP TABLE dbo.vw_AgencySpending",
        "SELECT * FROM sys.tables",
        "SELECT * FROM dbo.vw_AgencySpending UNION SELECT * FROM sys.tables",
        "EXEC xp_cmdshell 'whoami'",
        "SELECT * FROM dbo.vw_AgencySpending -- DROP TABLE dbo.Transactions",
        "SELECT * FROM dbo.vw_AgencySpending /* hidden DROP */",
    ],
)
def test_malicious_queries_are_rejected(sql):
    result = validate_sql(sql)
    assert not result.accepted
    assert result.reason


def test_unknown_view_is_rejected():
    result = validate_sql("SELECT * FROM dbo.Transactions")
    assert not result.accepted
    assert "not approved" in result.reason