"""Verifies the environment is correctly configured."""
import duckdb
from src.config import DB_PATH, CSV_PATH

print(f"DB_PATH:  {DB_PATH}")
print(f"CSV_PATH: {CSV_PATH}")
print(f"CSV exists: {CSV_PATH.exists()}")

con = duckdb.connect(str(DB_PATH))
result = con.execute("SELECT 'ok' AS status, version() AS duckdb_version").fetchone()
print(f"DuckDB:   {result}")
con.close()