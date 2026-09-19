"""Optional live evaluation for the text-to-SQL pipeline.

Run explicitly with:
    $env:RUN_TEXT2SQL_EVAL = "1"
    pytest -q tests/text2sql_eval.py -s
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import pytest

from app.text2sql.pipeline import answer_question
from app.text2sql.validator import validate_sql


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_view: str
    expected_columns: tuple[str, ...]


CASES = (
    EvalCase("Which agencies have the highest total obligations?", "vw_AgencySpending", ("Agency", "TotalObligations")),
    EvalCase("Show the top 10 agencies by spending.", "vw_AgencySpending", ("Agency", "TotalObligations")),
    EvalCase("What is the spending for each award type?", "vw_AwardTypeSpending", ("AwardType", "TotalObligations")),
    EvalCase("Which award type has the most transactions?", "vw_AwardTypeSpending", ("AwardType", "TransactionCount")),
    EvalCase("How much federal spending occurred in each fiscal year?", "vw_FederalSpendingByYear", ("FiscalYear", "TotalObligations")),
    EvalCase("Show annual federal obligations in chronological order.", "vw_FederalSpendingByYear", ("FiscalYear",)),
    EvalCase("How did spending change from one fiscal year to the next?", "vw_PeriodSpendingChange", ("FiscalYear", "PeriodChange")),
    EvalCase("Show the previous period and current period totals.", "vw_PeriodSpendingChange", ("PreviousPeriod", "TotalObligations")),
    EvalCase("Who are the highest-spending recipients?", "vw_RecipientSpendingRank", ("recipient_name", "TotalObligations")),
    EvalCase("List the top 10 recipients by spending rank.", "vw_RecipientSpendingRank", ("recipient_name", "SpendingRank")),
    EvalCase("What is the total spending for the top recipient?", "vw_RecipientSpendingRank", ("recipient_name", "TotalObligations")),
    EvalCase("Show recipient spending from highest to lowest.", "vw_RecipientSpendingRank", ("recipient_name", "TotalObligations")),
    EvalCase("How much did the top ten recipients receive?", "vw_Top10RecipientConcentration", ("Top10Spending",)),
    EvalCase("What percentage of spending went to the top ten recipients?", "vw_Top10RecipientConcentration", ("Top10Percentage",)),
    EvalCase("Compare total spending with top-ten spending.", "vw_Top10RecipientConcentration", ("TotalSpending", "Top10Spending")),
    EvalCase("Show the concentration percentage.", "vw_Top10RecipientConcentration", ("Top10Percentage",)),
    EvalCase("Give me agency spending totals, limited to five rows.", "vw_AgencySpending", ("Agency", "TotalObligations")),
    EvalCase("Give me award type transaction counts.", "vw_AwardTypeSpending", ("AwardType", "TransactionCount")),
    EvalCase("Show fiscal years and their spending changes.", "vw_PeriodSpendingChange", ("FiscalYear", "PeriodChange")),
    EvalCase("Rank recipients by total obligations.", "vw_RecipientSpendingRank", ("recipient_name", "SpendingRank")),
)


@pytest.mark.skipif(
    os.getenv("RUN_TEXT2SQL_EVAL") != "1",
    reason="Live Groq and SQL Server evaluation is opt-in; set RUN_TEXT2SQL_EVAL=1.",
)
def test_live_text2sql_evaluation():
    passed = 0
    failures: list[str] = []

    for case in CASES:
        result = answer_question(case.question)
        sql = result.sql or ""
        validation = validate_sql(sql) if sql else None
        columns = {column.lower() for column in (result.columns or [])}
        expected_columns = {column.lower() for column in case.expected_columns}
        ok = (
            result.error is None
            and case.expected_view.lower() in sql.lower()
            and validation is not None
            and validation.accepted
            and expected_columns.issubset(columns)
        )
        if ok:
            passed += 1
        else:
            failures.append(f"{case.question}: {result.error or 'unexpected SQL/result'}")

    rate = passed / len(CASES) * 100
    print(f"text2sql evaluation: {passed}/{len(CASES)} passed ({rate:.1f}%)")
    if failures:
        print("Failures:")
        print("\n".join(failures))
    assert passed == len(CASES), f"Evaluation pass rate was {rate:.1f}%"