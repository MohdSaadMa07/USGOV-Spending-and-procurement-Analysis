"""
app.main — FastAPI entry-point (Phase 2: read-only DB layer).

Endpoints:
  GET /              — service info
  GET /health        — DB reachability probe (safe, no credentials)
  GET /api/agency-spending — read-only query of existing analytical view

Run:
  uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
  or: python -m uvicorn app.main:app --reload

Config via .env — see .env.example
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query, Request
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_safe_config_summary, MAX_ROWS
from app.database import DBError, check_connection, execute_query
from app.text2sql.pipeline import RateLimiter, answer_question

logger = logging.getLogger(__name__)

app = FastAPI(
    title="USAspending AI Analytics API",
    description="Read-only FastAPI layer over USAspendingDB (SQL Server 2025). Phase 2: safe DB access only.",
    version="0.3.0",
)

_ask_rate_limiter = RateLimiter()
_ui_root = Path(__file__).resolve().parent.parent / "ui"
_ui_directory = _ui_root / "dist"
app.mount("/ui", StaticFiles(directory=_ui_directory, html=True), name="ui")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AskResponse(BaseModel):
    question: str
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    summary: str | None = None
    error: str | None = None

# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/", tags=["meta"])
def root():
    return {
        "service": "USAspending AI Analytics API",
        "phase": "Phase 3 — read-only text-to-SQL layer",
        "docs": "/docs",
        "health": "/health",
        "ui": "/ui/",
        "endpoints": ["/api/agency-spending", "/api/ask"],
    }

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
def health():
    """
    Returns healthy/unhealthy without exposing credentials.
    Checks that the app can reach SQL Server (SELECT 1).
    """
    ok = check_connection()
    # Include safe config summary (no secrets) for debugging deployment
    safe = get_safe_config_summary()
    if ok:
        return {"status": "healthy", "database": "reachable", "config": safe}
    # Use 503 so load balancers / monitors can detect degraded state
    return JSONResponse(
        status_code=503,
        content={"status": "unhealthy", "database": "unreachable", "config": safe},
    )

# ---------------------------------------------------------------------------
# Agency spending — read-only proof of pipeline
# ---------------------------------------------------------------------------

# Fixed, approved query — never built from user input. Uses existing view.
# vw_AgencySpending is the production view (GSA-only dataset currently).
# For fiscal-year filtering, we fall back to a direct parameterized grouping on Transactions.
_VIEW_SQL = "SELECT Agency, TotalObligations FROM dbo.vw_AgencySpending ORDER BY TotalObligations DESC;"

_FILTERED_SQL = """
SELECT
    awarding_agency_name AS Agency,
    SUM(federal_action_obligation) AS TotalObligations
FROM dbo.Transactions
WHERE awarding_agency_name IS NOT NULL
  AND action_date_fiscal_year = ?
GROUP BY awarding_agency_name
ORDER BY TotalObligations DESC;
"""

@app.get("/api/agency-spending", tags=["analytics"])
def agency_spending(
    fiscal_year: int | None = Query(default=None, description="Optional fiscal year filter (e.g. 2021). When omitted, uses vw_AgencySpending."),
    limit: int = Query(default=20, ge=1, le=500, description="Max rows to return (cap 500)."),
):
    """
    Return agency spending — simple read-only proof of the pipeline.
    - Without fiscal_year: queries the existing view dbo.vw_AgencySpending.
    - With fiscal_year: parameterized grouping on Transactions (still read-only).
    Both paths use pyodbc parameterized execution and respect MAX_ROWS.
    """
    try:
        # Clamp limit to global MAX_ROWS
        effective_limit = min(limit, MAX_ROWS)

        if fiscal_year is not None:
            # Parameterized — single ? placeholder, value bound safely
            rows: list[dict[str, Any]] = execute_query(_FILTERED_SQL, params=[fiscal_year], max_rows=effective_limit)
        else:
            # View already has TOP 20 inside definition, but we re-apply limit for safety.
            # execute_query will cap via fetchmany.
            rows = execute_query(_VIEW_SQL, max_rows=effective_limit)

        # Normalize float -> Python number (JSON serializable). Keep as float for now.
        # Ensure consistent keys for frontend.
        data = [
            {"agency": r.get("Agency") or r.get("agency"), "total_obligations": r.get("TotalObligations") or r.get("total_obligations")}
            for r in rows
        ]

        return {"count": len(data), "data": data, "source": "vw_AgencySpending" if fiscal_year is None else "Transactions (filtered)", "limit": effective_limit}

    except DBError as exc:
        # Safe message only — never surface raw DB error / conn string
        logger.warning("agency-spending DB error: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": str(exc)})
    except Exception:  # pragma: no cover
        logger.exception("unexpected error in agency-spending")
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.post("/api/ask", response_model=AskResponse, tags=["analytics"])
def ask(request: Request, payload: AskRequest):
    """Generate and execute one validated, read-only query over analytical views."""
    client_host = request.client.host if request.client else "unknown"
    if not _ask_rate_limiter.allow(client_host):
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Try again later."})

    result = answer_question(payload.question)
    outcome = "success" if result.error is None else "error"
    logger.info("text2sql question=%r sql=%r outcome=%s", payload.question, result.sql, outcome)
    return AskResponse(
        question=result.question,
        sql=result.sql,
        columns=result.columns or [],
        rows=result.rows or [],
        row_count=result.row_count,
        summary=result.summary,
        error=result.error,
    )
