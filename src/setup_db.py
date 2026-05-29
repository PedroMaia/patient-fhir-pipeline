"""Creates the database schema by running DDL scripts."""
import logging
from pathlib import Path

from config import PROJECT_ROOT, LOG_LEVEL
from db import run_sql_file

logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

SQL_DIR = PROJECT_ROOT / "sql"

DDL_FILES = [
    "01_create_patient.sql",
    # 02_create_fhir_patient.sql will be added in Part 3
]

def main() -> None:
    for filename in DDL_FILES:
        path = SQL_DIR / filename
        log.info(f"Running {filename}")
        run_sql_file(path)
    log.info("Schema setup complete.")


if __name__ == "__main__":
    main()