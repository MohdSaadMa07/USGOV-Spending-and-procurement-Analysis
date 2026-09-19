from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.database import DBQueryError
from app.main import app
from app.text2sql.pipeline import RateLimiter, answer_question


class FakeProvider:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.errors = []

    def generate_sql(self, question, schema_prompt, error=None):
        self.errors.append(error)
        return next(self.responses)


def test_pipeline_executes_validated_sql():
    provider = FakeProvider(["SELECT Agency FROM dbo.vw_AgencySpending"])
    execute = Mock(return_value=[{"Agency": "GSA"}])
    result = answer_question("Which agency spends the most?", provider=provider, execute=execute)
    assert result.error is None
    assert result.columns == ["Agency"]
    assert result.row_count == 1
    execute.assert_called_once()
    assert "TOP 500" in execute.call_args.args[0]


def test_pipeline_retries_once_after_database_error():
    provider = FakeProvider(
        [
            "SELECT bad_column FROM dbo.vw_AgencySpending",
            "SELECT Agency FROM dbo.vw_AgencySpending",
        ]
    )
    execute = Mock(side_effect=[DBQueryError("Database query failed."), [{"Agency": "GSA"}]])
    result = answer_question("Show agencies", provider=provider, execute=execute)
    assert result.error is None
    assert execute.call_count == 2
    assert provider.errors == [None, "Database query failed."]


def test_pipeline_rejects_unanswerable_sql_without_execution():
    provider = FakeProvider(["SELECT * FROM dbo.Transactions"])
    execute = Mock()
    result = answer_question("Show private data", provider=provider, execute=execute)
    assert execute.call_count == 0
    assert "cannot answer" in result.error


def test_rate_limiter():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("client")
    assert limiter.allow("client")
    assert not limiter.allow("client")
    assert limiter.allow("other-client")


def test_ask_endpoint_with_mocked_pipeline():
    client = TestClient(app)
    with patch("app.main.answer_question") as mocked:
        mocked.return_value = type(
            "Result",
            (),
            {
                "question": "Show spending",
                "sql": "SELECT TOP 500 * FROM dbo.vw_FederalSpendingByYear",
                "columns": ["FiscalYear"],
                "rows": [{"FiscalYear": 2025}],
                "row_count": 1,
                "summary": None,
                "error": None,
            },
        )()
        response = client.post("/api/ask", json={"question": "Show spending"})
    assert response.status_code == 200
    assert response.json()["row_count"] == 1


def test_ask_endpoint_validates_question_length():
    client = TestClient(app)
    response = client.post("/api/ask", json={"question": "x" * 1001})
    assert response.status_code == 422