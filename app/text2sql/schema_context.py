"""Build the text-to-SQL schema prompt from the approved SQL views."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.database import get_connection

LIVE_VIEW_NAMES = (
    "vw_AgencySpending",
    "vw_AwardTypeSpending",
    "vw_FederalSpendingByYear",
    "vw_PeriodSpendingChange",
    "vw_RecipientSpendingRank",
    "vw_Top10RecipientConcentration",
)

VIEW_DESCRIPTIONS = {
    "vw_AgencySpending": "Top agencies ranked by total federal obligations.",
    "vw_AwardTypeSpending": "Transaction counts and obligations grouped by award type.",
    "vw_FederalSpendingByYear": "Total federal obligations grouped by fiscal year.",
    "vw_PeriodSpendingChange": "Fiscal-year totals with change from the previous year.",
    "vw_RecipientSpendingRank": "Recipients ranked by total federal obligations.",
    "vw_Top10RecipientConcentration": "Overall share of obligations concentrated among the top ten recipients.",
}

EXAMPLE_QUESTIONS = (
    (
        "Which agencies had the highest spending in FY2025?",
        "SELECT TOP 10 Agency, TotalObligations FROM dbo.vw_AgencySpending ORDER BY TotalObligations DESC;",
    ),
    (
        "How much was spent in each fiscal year?",
        "SELECT FiscalYear, TotalObligations FROM dbo.vw_FederalSpendingByYear ORDER BY FiscalYear;",
    ),
    (
        "How did spending change between fiscal years?",
        "SELECT FiscalYear, TotalObligations, PreviousPeriod, PeriodChange FROM dbo.vw_PeriodSpendingChange ORDER BY FiscalYear;",
    ),
    (
        "Which award types received the most spending?",
        "SELECT AwardType, TransactionCount, TotalObligations FROM dbo.vw_AwardTypeSpending ORDER BY TotalObligations DESC;",
    ),
    (
        "Who are the top recipients by spending?",
        "SELECT TOP 10 recipient_name, TotalObligations, SpendingRank FROM dbo.vw_RecipientSpendingRank ORDER BY SpendingRank;",
    ),
    (
        "What percentage is concentrated among the top ten recipients?",
        "SELECT Top10Spending, TotalSpending, Top10Percentage FROM dbo.vw_Top10RecipientConcentration;",
    ),
    (
        "Which agencies are in the top five by obligations?",
        "SELECT TOP 5 Agency, TotalObligations FROM dbo.vw_AgencySpending ORDER BY TotalObligations DESC;",
    ),
    (
        "How many transactions are recorded for each award type?",
        "SELECT AwardType, TransactionCount FROM dbo.vw_AwardTypeSpending ORDER BY TransactionCount DESC;",
    ),
)


@dataclass(frozen=True)
class ViewColumn:
    name: str
    data_type: str


def get_whitelisted_view_names() -> tuple[str, ...]:
    """Return the views verified to exist in the production database."""
    return LIVE_VIEW_NAMES


def _format_data_type(row: Any) -> str:
    data_type = str(row[1])
    length = row[2]
    precision = row[3]
    scale = row[4]
    if length is not None and data_type.lower() in {"char", "varchar", "nchar", "nvarchar", "binary", "varbinary"}:
        return f"{data_type}({length if length != -1 else 'max'})"
    if precision is not None and scale is not None and data_type.lower() in {"decimal", "numeric"}:
        return f"{data_type}({precision},{scale})"
    return data_type


def load_view_columns(connection: Any | None = None) -> dict[str, tuple[ViewColumn, ...]]:
    """Read column metadata for the approved views from SQL Server."""
    context = get_connection() if connection is None else None
    conn = context.__enter__() if context else connection
    try:
        result: dict[str, tuple[ViewColumn, ...]] = {}
        for view_name in get_whitelisted_view_names():
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                       NUMERIC_PRECISION, NUMERIC_SCALE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION;
                """,
                [view_name],
            )
            result[view_name] = tuple(
                ViewColumn(name=str(row[0]), data_type=_format_data_type(row))
                for row in cursor.fetchall()
            )
            cursor.close()
        return result
    finally:
        if context:
            context.__exit__(None, None, None)


def build_schema_prompt(columns_by_view: dict[str, tuple[ViewColumn, ...]] | None = None) -> str:
    """Render the schema, descriptions, and examples used by the SQL generator."""
    if columns_by_view is None:
        columns_by_view = load_view_columns()

    sections = [
        "You generate read-only Microsoft T-SQL for the approved dbo views below.",
        "Use only these views. Return exactly one SELECT or WITH...SELECT statement.",
        "Never use DML, DDL, system objects, EXEC, comments, or multiple statements.",
        "",
        "APPROVED VIEWS:",
    ]
    for view_name in get_whitelisted_view_names():
        columns = columns_by_view.get(view_name, ())
        column_text = ", ".join(f"{column.name} {column.data_type}" for column in columns) or "column metadata unavailable"
        sections.append(f"- dbo.{view_name}: {VIEW_DESCRIPTIONS.get(view_name, 'Analytical spending view.')}")
        sections.append(f"  Columns: {column_text}")

    sections.append("\nEXAMPLES:")
    for question, sql in EXAMPLE_QUESTIONS:
        sections.append(f"Q: {question}\nSQL: {sql}")
    return "\n".join(sections)