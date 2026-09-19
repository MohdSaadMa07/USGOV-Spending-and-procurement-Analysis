"""Question-to-SQL pipeline with validation, retry, and simple rate limiting."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from app.config import MAX_ROWS
from app.database import DBError, execute_query
from app.text2sql.llm import LLMError, LLMProvider, get_llm_provider
from app.text2sql.schema_context import build_schema_prompt
from app.text2sql.validator import validate_sql

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 1000
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_REQUESTS = 30


@dataclass(frozen=True)
class PipelineResult:
    question: str
    sql: str | None = None
    columns: list[str] | None = None
    rows: list[dict[str, Any]] | None = None
    row_count: int = 0
    summary: str | None = None
    error: str | None = None


class RateLimiter:
    def __init__(self, max_requests: int = RATE_LIMIT_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, client_id: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            recent = [stamp for stamp in self._requests.get(client_id, []) if stamp > cutoff]
            allowed = len(recent) < self.max_requests
            if allowed:
                recent.append(now)
            self._requests[client_id] = recent
            return allowed


def _strip_code_fence(sql: str) -> str:
    value = sql.strip()
    if value.startswith("```") and value.endswith("```"):
        lines = value.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```sql", "```tsql"}:
            return "\n".join(lines[1:-1]).strip()
    return value


def answer_question(
    question: str,
    provider: LLMProvider | None = None,
    execute: Callable[..., list[dict[str, Any]]] = execute_query,
) -> PipelineResult:
    """Generate, validate, and execute SQL, retrying one time after a DB error."""
    question = question.strip()
    if not question:
        return PipelineResult(question=question, error="Question cannot be empty.")
    if len(question) > MAX_QUESTION_LENGTH:
        return PipelineResult(question=question, error=f"Question must be {MAX_QUESTION_LENGTH} characters or fewer.")

    try:
        schema_prompt = build_schema_prompt()
        active_provider = provider or get_llm_provider()
        generated_sql = _strip_code_fence(active_provider.generate_sql(question, schema_prompt))
    except LLMError as exc:
        return PipelineResult(question=question, error=str(exc))
    except DBError:
        return PipelineResult(question=question, error="Unable to load the analytics schema.")

    for attempt in range(2):
        validation = validate_sql(generated_sql)
        if not validation.accepted:
            return PipelineResult(question=question, sql=generated_sql, error=f"I cannot answer from these views: {validation.reason}")

        cleaned_sql = validation.cleaned_sql
        try:
            rows = execute(cleaned_sql, max_rows=MAX_ROWS)
            columns = list(rows[0].keys()) if rows else []
            return PipelineResult(
                question=question,
                sql=cleaned_sql,
                columns=columns,
                rows=rows,
                row_count=len(rows),
            )
        except DBError as exc:
            if attempt == 0:
                try:
                    generated_sql = _strip_code_fence(active_provider.generate_sql(question, schema_prompt, error=str(exc)))
                    continue
                except LLMError as retry_exc:
                    return PipelineResult(question=question, sql=cleaned_sql, error=str(retry_exc))
            return PipelineResult(question=question, sql=cleaned_sql, error="The generated query could not be executed.")

    return PipelineResult(question=question, error="The question could not be answered.")