"""Runs the FHIR transformation: patient -> fhir_patient."""
import logging

from config import PROJECT_ROOT, LOG_LEVEL
from db import get_connection

logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

TRANSFORM_SQL = PROJECT_ROOT / "sql" / "transform_fhir_patient.sql"
TRANSFORM_SQL_HISTORY = PROJECT_ROOT / "sql" / "transform_fhir_patient_history.sql"


def main() -> None:
    log.info(f"Running transformation: {TRANSFORM_SQL.name}")

    sql = TRANSFORM_SQL.read_text(encoding="utf-8")
    sql_history = TRANSFORM_SQL_HISTORY.read_text(encoding="utf-8")

    with get_connection() as con:
        # Optional: ensure fhir_patient exists (defensive)
        ddl = (PROJECT_ROOT / "sql" / "02_create_fhir_patient.sql").read_text()
        con.execute(ddl)

        con.execute(sql)
        con.execute(sql_history)

        count         = con.execute("SELECT COUNT(*) FROM fhir_patient").fetchone()[0]
        count_history = con.execute("SELECT COUNT(*) FROM fhir_patient_history").fetchone()[0]
        log.info(f"fhir_patient: {count} rows | fhir_patient_history: {count_history} rows")

if __name__ == "__main__":
    main()