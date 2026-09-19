"""
Tests for GET /health — uses mocks so no real DB required.
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_healthy():
    with patch("app.main.check_connection", return_value=True):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["database"] == "reachable"
        # config must be present but must NOT contain password
        assert "config" in body
        assert "sql_password" not in str(body).lower()
        assert "pwd" not in str(body).lower()


def test_health_unhealthy_returns_503():
    with patch("app.main.check_connection", return_value=False):
        resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "unhealthy"
        assert body["database"] == "unreachable"


def test_health_has_no_secrets():
    with patch("app.main.check_connection", return_value=True):
        resp = client.get("/health")
        text = resp.text.lower()
        # ensure no password-like leakage
        assert "password" not in text
        # safe summary keys
        assert "sql_server" in text or "sql_database" in text


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "service" in resp.json()
