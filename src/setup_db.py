"""Creates the database schema by running DDL scripts."""
import logging
from pathlib import Path

from config import PROJECT_ROOT, DB_PATH
from db import run_sql_file

SQL_DIR = PROJECT_ROOT / "sql"

DDL_FILES = [
    "01_create_patient.sql",
    "02_create_fhir_patient.sql",
    "03_create_fhir_patient_history.sql",
    "04_create_pipeline_control.sql",
]


def _get_logger():
    try:
        from prefect import get_run_logger
        return get_run_logger()
    except Exception:
        return logging.getLogger(__name__)


def main() -> None:
    log = _get_logger()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    for filename in DDL_FILES:
        path = SQL_DIR / filename
        log.info(f"Running {filename}")
        run_sql_file(path)

    log.info("Schema setup complete.")


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(levelname)s | %(message)s")
    main()
