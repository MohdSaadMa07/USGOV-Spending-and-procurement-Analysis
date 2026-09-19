"""
Tests for GET /api/agency-spending — read-only pipeline.
All DB calls are mocked — no real SQL Server required.
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.database import DBError

client = TestClient(app)

SAMPLE_ROWS = [
    {"Agency": "General Services Administration", "TotalObligations": 104652184748.29},
]


def test_agency_spending_no_filter():
    with patch("app.main.execute_query", return_value=SAMPLE_ROWS) as mock:
        resp = client.get("/api/agency-spending")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["data"][0]["agency"] == "General Services Administration"
        assert body["source"] == "vw_AgencySpending"
        # verify read-only view SQL path was used (no fiscal_year param)
        assert mock.call_count == 1
        args, kwargs = mock.call_args
        assert "vw_AgencySpending" in args[0]


def test_agency_spending_with_fiscal_year_param():
    with patch("app.main.execute_query", return_value=SAMPLE_ROWS) as mock:
        resp = client.get("/api/agency-spending?fiscal_year=2021")
        assert resp.status_code == 200
        body = resp.json()
        assert body["source"] == "Transactions (filtered)"
        # ensure parameterized execution: params contain fiscal year
        args, kwargs = mock.call_args
        assert kwargs.get("params") == [2021] or args[1] == [2021]


def test_agency_spending_limit_clamped():
    with patch("app.main.execute_query", return_value=[]) as mock:
        resp = client.get("/api/agency-spending?limit=500")
        assert resp.status_code == 200
        # limit > MAX_ROWS should be clamped internally — but 500 is allowed
        assert resp.json()["limit"] == 500

    # >500 should be rejected by validation (FastAPI 422) — our Query le=500
    resp = client.get("/api/agency-spending?limit=1000")
    assert resp.status_code == 422


def test_agency_spending_db_error_returns_503():
    with patch("app.main.execute_query", side_effect=DBError("Unable to connect to database.")):
        resp = client.get("/api/agency-spending")
        assert resp.status_code == 503
        assert "detail" in resp.json()


def test_agency_spending_empty_result():
    with patch("app.main.execute_query", return_value=[]):
        resp = client.get("/api/agency-spending?fiscal_year=1900")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0
        assert resp.json()["data"] == []
