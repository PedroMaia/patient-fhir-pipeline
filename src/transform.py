"""Runs the FHIR transformation: patient -> fhir_patient + fhir_patient_history."""
import logging

from config import PROJECT_ROOT
from db import get_connection

TRANSFORM_FILES = {
    "fhir_patient": {
        "merge":           PROJECT_ROOT / "sql" / "transform_fhir_patient_merge.sql",
        "truncate_insert": PROJECT_ROOT / "sql" / "transform_fhir_patient.sql",
    },
    "fhir_patient_history": {
        "merge":           PROJECT_ROOT / "sql" / "transform_fhir_patient_history_merge.sql",
        "truncate_insert": PROJECT_ROOT / "sql" / "transform_fhir_patient_history.sql",
    },
}


def _get_logger():
    try:
        from prefect import get_run_logger
        return get_run_logger()
    except Exception:
        return logging.getLogger(__name__)


def get_strategy(con, table_name: str) -> str:
    row = con.execute(
        "SELECT strategy FROM pipeline_control WHERE table_name = ?", [table_name]
    ).fetchone()
    if not row:
        raise ValueError(f"No pipeline_control entry for table: {table_name}")
    return row[0]


def run_transform(con, table_name: str) -> None:
    log = _get_logger()
    strategy = get_strategy(con, table_name)
    log.info(f"{table_name} → strategy: {strategy}")

    if strategy == "truncate_insert":
        if table_name == "fhir_patient":
            con.execute("DELETE FROM fhir_patient_history")
            log.info("Truncated fhir_patient_history (FK dependency)")
            con.execute("DELETE FROM fhir_patient")
            log.info("Truncated fhir_patient")
        elif table_name == "fhir_patient_history":
            con.execute("DELETE FROM fhir_patient_history")
            log.info("Truncated fhir_patient_history")

    sql = TRANSFORM_FILES[table_name][strategy].read_text(encoding="utf-8")
    con.execute(sql)


def main() -> None:
    log = _get_logger()
    with get_connection() as con:
        count_before         = con.execute("SELECT COUNT(*) FROM fhir_patient").fetchone()[0]
        count_history_before = con.execute("SELECT COUNT(*) FROM fhir_patient_history").fetchone()[0]

        run_transform(con, "fhir_patient")
        run_transform(con, "fhir_patient_history")

        count_after         = con.execute("SELECT COUNT(*) FROM fhir_patient").fetchone()[0]
        count_history_after = con.execute("SELECT COUNT(*) FROM fhir_patient_history").fetchone()[0]

    log.info(f"fhir_patient: {count_after} rows (+{count_after - count_before} added)")
    log.info(f"fhir_patient_history: {count_history_after} rows (+{count_history_after - count_history_before} added)")


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(levelname)s | %(message)s")
    main()
