"""
app.config — environment-based configuration (python-dotenv).

All settings come from environment variables / .env file.
No secrets are hardcoded. See .env.example for required keys.

Deployment-friendly:
  - SQL_SERVER / SQL_DATABASE / SQL_DRIVER configurable (no localhost in code)
  - Supports both Windows Trusted_Connection and SQL auth (UID/PWD)
  - Azure SQL will just need different SQL_SERVER / SQL_DATABASE values
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root if present. Does not override already-set env vars.
# Path: <project_root>/.env
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)


def _get_env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    if val is None:
        return default
    # treat empty string as missing
    val = val.strip()
    return val if val != "" else default


# ---------------------------------------------------------------------------
# SQL Server
# ---------------------------------------------------------------------------
SQL_SERVER: str = _get_env("SQL_SERVER", "localhost") or "localhost"
SQL_DATABASE: str = _get_env("SQL_DATABASE", "USAspendingDB") or "USAspendingDB"
SQL_DRIVER: str = _get_env("SQL_DRIVER", "ODBC Driver 18 for SQL Server") or "ODBC Driver 18 for SQL Server"

# Optional SQL auth — when empty, use Windows Trusted_Connection
SQL_USERNAME: str | None = _get_env("SQL_USERNAME")
SQL_PASSWORD: str | None = _get_env("SQL_PASSWORD")

# Explicit toggles (defaults work for local SQL Server 2025)
SQL_TRUSTED_CONNECTION: str = _get_env("SQL_TRUSTED_CONNECTION", "") or ""
SQL_TRUST_SERVER_CERTIFICATE: str = _get_env("SQL_TRUST_SERVER_CERTIFICATE", "yes") or "yes"

# Timeouts (seconds) — read-only queries should never run long
SQL_CONNECTION_TIMEOUT: int = int(_get_env("SQL_CONNECTION_TIMEOUT", "30") or "30")
SQL_QUERY_TIMEOUT: int = int(_get_env("SQL_QUERY_TIMEOUT", "30") or "30")

# Safety cap for any API response
MAX_ROWS: int = int(_get_env("MAX_ROWS", "500") or "500")

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
API_HOST: str = _get_env("API_HOST", "127.0.0.1") or "127.0.0.1"
API_PORT: int = int(_get_env("API_PORT", "8000") or "8000")

# ---------------------------------------------------------------------------
# Text-to-SQL LLM
# ---------------------------------------------------------------------------
LLM_PROVIDER: str = _get_env("LLM_PROVIDER", "groq") or "groq"
LLM_API_KEY: str | None = _get_env("LLM_API_KEY")
LLM_MODEL: str = _get_env("LLM_MODEL", "openai/gpt-oss-20b") or "openai/gpt-oss-20b"
LLM_BASE_URL: str | None = _get_env("LLM_BASE_URL")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_sql_auth_configured() -> bool:
    """True if UID/PWD should be used instead of Trusted_Connection."""
    return bool(SQL_USERNAME and SQL_PASSWORD)


def get_connection_string() -> str:
    """
    Build an ODBC connection string from env vars.
    Never logs or returns password in clear text outside this function.
    """
    parts = [
        f"DRIVER={{{SQL_DRIVER}}}",
        f"SERVER={SQL_SERVER}",
        f"DATABASE={SQL_DATABASE}",
        f"Connection Timeout={SQL_CONNECTION_TIMEOUT}",
    ]

    if is_sql_auth_configured():
        parts.append(f"UID={SQL_USERNAME}")
        parts.append(f"PWD={SQL_PASSWORD}")
        # For SQL auth on Azure, encryption is required; keep TrustServerCertificate configurable
        if SQL_TRUST_SERVER_CERTIFICATE.lower() in ("yes", "true", "1"):
            parts.append("TrustServerCertificate=yes")
        parts.append("Encrypt=yes")
    else:
        # Windows / Integrated auth — use Trusted_Connection.
        # Allow explicit override via SQL_TRUSTED_CONNECTION env.
        trusted = SQL_TRUSTED_CONNECTION if SQL_TRUSTED_CONNECTION else "yes"
        parts.append(f"Trusted_Connection={trusted}")
        if SQL_TRUST_SERVER_CERTIFICATE.lower() in ("yes", "true", "1"):
            parts.append("TrustServerCertificate=yes")

    return ";".join(parts) + ";"


def get_safe_config_summary() -> dict:
    """
    Safe to return from /health — never includes password.
    """
    return {
        "sql_server": SQL_SERVER,
        "sql_database": SQL_DATABASE,
        "sql_driver": SQL_DRIVER,
        "api_host": API_HOST,
        "api_port": API_PORT,
        "sql_auth_mode": "sql_auth" if is_sql_auth_configured() else "trusted_connection",
        "connection_timeout": SQL_CONNECTION_TIMEOUT,
        "query_timeout": SQL_QUERY_TIMEOUT,
        "max_rows": MAX_ROWS,
    }
