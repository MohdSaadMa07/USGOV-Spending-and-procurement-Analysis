"""Validation and normalization for LLM-generated read-only T-SQL."""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from app.text2sql.schema_context import get_whitelisted_view_names

MAX_TOP = 500
_COMMENT_MARKERS = ("--", "/*", "*/")
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(?:ALTER|BACKUP|CREATE|DELETE|DROP|EXEC|EXECUTE|GRANT|INSERT|MERGE|RESTORE|REVOKE|TRUNCATE|UPDATE|INTO)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ValidationResult:
    cleaned_sql: str | None = None
    reason: str | None = None

    @property
    def accepted(self) -> bool:
        return self.cleaned_sql is not None


def _reject(reason: str) -> ValidationResult:
    return ValidationResult(reason=reason)


def _top_value(select: exp.Select) -> int | None:
    limit = select.args.get("limit")
    if limit is None or not isinstance(limit.expression, exp.Literal) or not limit.expression.is_number:
        return None
    return int(limit.expression.this)


def _apply_top_limit(tree: exp.Expression) -> None:
    for select in tree.find_all(exp.Select):
        value = _top_value(select)
        if value is None or value > MAX_TOP:
            select.set("limit", exp.Limit(expression=exp.Literal.number(MAX_TOP)))


def _cte_names(tree: exp.Expression) -> set[str]:
    return {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE) if cte.alias_or_name}


def validate_sql(sql: str) -> ValidationResult:
    """Validate one generated SQL statement and return normalized T-SQL."""
    if not isinstance(sql, str) or not sql.strip():
        return _reject("SQL is empty.")
    if any(marker in sql for marker in _COMMENT_MARKERS):
        return _reject("SQL comments are not allowed.")
    if _FORBIDDEN_KEYWORDS.search(sql) or re.search(r"\bxp_cmdshell\b", sql, re.IGNORECASE):
        return _reject("DML, DDL, EXEC, INTO, and shell execution are not allowed.")

    try:
        statements = parse(sql, read="tsql")
    except ParseError as exc:
        return _reject(f"SQL could not be parsed: {exc.errors[0].get('description', 'invalid syntax')}")

    if len(statements) != 1:
        return _reject("Exactly one SQL statement is required.")

    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        return _reject("Only SELECT or WITH...SELECT statements are allowed.")

    cte_names = _cte_names(tree)
    allowed_views = {name.lower() for name in get_whitelisted_view_names()}
    for table in tree.find_all(exp.Table):
        table_name = table.name.lower()
        schema_name = (table.db or "").lower()
        if table_name in cte_names and not schema_name:
            continue
        if schema_name != "dbo" or table_name not in allowed_views:
            return _reject(f"Table or view is not approved: {table.sql(dialect='tsql')}.")

    _apply_top_limit(tree)
    return ValidationResult(cleaned_sql=tree.sql(dialect="tsql"))