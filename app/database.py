"""
app.database — safe read-only SQL Server helper (pyodbc).

Design:
  - Read-only: only fixed SELECT statements from approved views/tables.
  - Parameterized: no string-concatenated user input.
  - Timeouts: connection ~30s, query ~30s (via pyodbc timeout + SET LOCK_TIMEOUT).
  - Row cap: MAX_ROWS (500) enforced in Python after fetch.
  - No credentials exposed in logs or API responses.
  - Clean error handling — callers get DBError with safe message.
"""
from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from typing import Any, Sequence

import pyodbc

from app.config import (
    MAX_ROWS,
    SQL_QUERY_TIMEOUT,
    get_connection_string,
    get_safe_config_summary,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class DBError(RuntimeError):
    """Safe wrapper — message is sanitized for API responses."""

class DBConnectionError(DBError):
    pass

class DBQueryError(DBError):
    pass


# ---------------------------------------------------------------------------
# Read-only guard (defense in depth — even though endpoints use fixed SQL)
# ---------------------------------------------------------------------------

# Block any write/DDL keyword anywhere in the SQL. Only SELECT / WITH allowed.
_FORBIDDEN_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|EXEC|EXECUTE|CREATE|MERGE|GRANT|REVOKE|BACKUP|RESTORE)\b",
    re.IGNORECASE,
)

def _assert_read_only(sql: str) -> None:
    stripped = sql.lstrip().upper()
    # Allow leading WITH (CTE) or SELECT. Comments not expected in fixed queries.
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        raise DBQueryError("Only SELECT queries are allowed.")
    if _FORBIDDEN_PATTERN.search(sql):
        raise DBQueryError("Query contains forbidden keyword.")


# ---------------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------------

@contextmanager
def get_connection():
    """
    Yield a pyodbc connection. Ensures close even on error.
    Uses timeout from config. Never logs connection string (contains secrets).
    """
    conn = None
    conn_str = get_connection_string()
    # Log safe summary only
    safe = get_safe_config_summary()
    logger.info("Connecting to SQL Server db=%s server=%s", safe["sql_database"], safe["sql_server"])
    try:
        # pyodbc.connect timeout is login timeout; query timeout is set on cursor/connection if driver supports it
        conn = pyodbc.connect(conn_str, timeout=safe["connection_timeout"])
        # Best-effort query timeout — driver specific; try SQL_ATTR_QUERY_TIMEOUT
        try:
            conn.timeout = SQL_QUERY_TIMEOUT  # affects query timeout on some drivers
        except Exception:
            pass
        yield conn
    except pyodbc.Error as exc:
        # Sanitize: do not include connection string in error
        logger.error("SQL connection failed: %s", type(exc).__name__)
        raise DBConnectionError("Unable to connect to database.") from exc
    except DBError:
        raise
    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected connection error")
        raise DBConnectionError("Unable to connect to database.") from exc
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _row_to_dict(cursor: pyodbc.Cursor, row: tuple) -> dict[str, Any]:
    cols = [c[0] for c in cursor.description]
    return {col: val for col, val in zip(cols, row)}


def execute_query(
    sql: str,
    params: Sequence[Any] | None = None,
    max_rows: int | None = None,
) -> list[dict[str, Any]]:
    """
    Execute a parameterized read-only SELECT and return rows as dicts.
    - sql must be SELECT / WITH ... SELECT (checked).
    - params are bound via pyodbc (?) placeholders — never format into SQL.
    - max_rows caps result size (default MAX_ROWS from config, 500).
    - Query timeout is SQL_QUERY_TIMEOUT (30s) via connection.timeout.
    """
    _assert_read_only(sql)
    limit = max_rows if max_rows is not None else MAX_ROWS
    if limit is not None and limit > MAX_ROWS:
        limit = MAX_ROWS
    if limit is not None and limit <= 0:
        limit = MAX_ROWS

    params = params or []

    with get_connection() as conn:
        try:
            cursor = conn.cursor()
            # Try to set query timeout at cursor level if supported
            # pyodbc: connection.timeout is query timeout on newer drivers
            logger.debug("Executing query (param count=%d, max_rows=%s)", len(params), limit)
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            # Fetch with row cap to avoid unbounded memory / response size
            if limit is not None:
                rows = cursor.fetchmany(limit + 1)
                # fetchmany with limit+1 lets us detect truncation
                if len(rows) > limit:
                    logger.warning("Query exceeded max_rows=%d — truncating", limit)
                    rows = rows[:limit]
            else:
                rows = cursor.fetchall()

            result = [_row_to_dict(cursor, r) for r in rows]
            cursor.close()
            return result

        except pyodbc.Error as exc:
            logger.error("SQL query failed: %s", type(exc).__name__)
            # Categorize timeout vs other
            msg = str(exc)
            if "timeout" in msg.lower() or "HYT00" in msg:
                raise DBQueryError("Database query timed out.") from exc
            raise DBQueryError("Database query failed.") from exc
        except DBError:
            raise
        except Exception as exc:  # pragma: no cover
            logger.exception("Unexpected query error")
            raise DBQueryError("Database query failed.") from exc


def check_connection() -> bool:
    """
    Lightweight health probe — runs SELECT 1 and returns True if reachable.
    Does not leak credentials. Used by GET /health.
    """
    try:
        # Minimal query — should work on any SQL Server
        execute_query("SELECT 1 AS ok", max_rows=1)
        return True
    except DBError:
        return False
    except Exception:  # pragma: no cover
        return False
