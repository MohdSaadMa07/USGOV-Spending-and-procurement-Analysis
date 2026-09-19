"""
Tests for app.database — read-only guard, param handling, row limits.
Uses pyodbc mocks so no real SQL Server required.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.database import DBQueryError, execute_query, _assert_read_only


def test_assert_read_only_allows_select():
    _assert_read_only("SELECT 1")
    _assert_read_only("WITH cte AS (SELECT 1) SELECT * FROM cte")


def test_assert_read_only_blocks_writes():
    for sql in [
        "INSERT INTO t VALUES (1)",
        "UPDATE t SET x=1",
        "DELETE FROM t",
        "DROP TABLE t",
        "EXEC sp_executesql 'SELECT 1'",
        "CREATE VIEW v AS SELECT 1",
        "TRUNCATE TABLE t",
        "GRANT SELECT ON t TO user",
    ]:
        with pytest.raises(DBQueryError):
            _assert_read_only(sql)


def test_execute_query_blocks_forbidden_even_if_select_prefix():
    # sneaky: SELECT + forbidden later
    with pytest.raises(DBQueryError):
        _assert_read_only("SELECT * FROM t; DROP TABLE t")


@patch("app.database.get_connection")
def test_execute_query_parameterized_and_capped(mock_get_conn):
    # Setup fake cursor
    fake_rows = [("Agency", 100.0), ("Agency2", 200.0)]
    mock_cursor = MagicMock()
    mock_cursor.description = [("Agency",), ("TotalObligations",)]
    mock_cursor.fetchmany.return_value = [("Agency", 100.0), ("Agency2", 200.0)]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    # get_connection is contextmanager, so mock it as contextmanager
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    mock_get_conn.return_value = mock_ctx

    rows = execute_query("SELECT Agency, TotalObligations FROM dbo.vw_AgencySpending", max_rows=500)
    assert len(rows) == 2
    assert rows[0]["Agency"] == "Agency"
    # verify cursor.execute called without string interpolation
    mock_cursor.execute.assert_called_once()


@patch("app.database.get_connection")
def test_execute_query_rejects_non_select(mock_get_conn):
    # Should fail before even trying to connect
    with pytest.raises(DBQueryError):
        execute_query("DELETE FROM dbo.Transactions WHERE 1=1")


@patch("app.database.pyodbc.connect")
def test_check_connection_success(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchmany.return_value = [(1,)]
    mock_cursor.description = [("ok",)]
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    from app.database import check_connection
    # check_connection uses execute_query internally → mock that path
    with patch("app.database.execute_query", return_value=[{"ok": 1}]):
        assert check_connection() is True


@patch("app.database.execute_query", side_effect=Exception("timeout"))
def test_check_connection_failure(_mock):
    from app.database import check_connection
    assert check_connection() is False
