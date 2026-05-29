"""Database connection helper."""
import duckdb
from pathlib import Path
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_connection():
    """Yields a DuckDB connection and closes it after use."""
    con = duckdb.connect(str(DB_PATH))
    try:
        yield con
    finally:
        con.close()


def run_sql_file(sql_path: Path) -> None:
    """Executes all statements in a .sql file."""
    sql = Path(sql_path).read_text(encoding="utf-8")
    with get_connection() as con:
        con.execute(sql)