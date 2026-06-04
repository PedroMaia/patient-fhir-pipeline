"""Tests for environment configuration and DuckDB connectivity."""
import duckdb
import pytest
from config import DB_PATH, CSV_PATH


def test_db_path_is_configured():
    assert DB_PATH is not None


def test_csv_path_is_configured():
    assert CSV_PATH is not None


def test_csv_file_exists():
    assert CSV_PATH.exists(), f"CSV not found at {CSV_PATH}"


def test_duckdb_connects():
    con = duckdb.connect(str(DB_PATH))
    result = con.execute("SELECT 'ok'").fetchone()
    con.close()
    assert result[0] == "ok"


def test_duckdb_version_is_returned():
    con = duckdb.connect(str(DB_PATH))
    result = con.execute("SELECT version()").fetchone()
    con.close()
    assert result[0] is not None
