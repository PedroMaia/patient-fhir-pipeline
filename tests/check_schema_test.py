"""Tests for database schema — requires the pipeline to have been initialised (setup_db.py)."""
import duckdb
import pytest
from config import DB_PATH


EXPECTED_TABLES = {"patient", "fhir_patient", "fhir_patient_history", "pipeline_control"}

PATIENT_COLUMNS = {
    "id", "first_name", "last_name", "birth_date", "gender",
    "address", "city", "state", "zip_code", "phone_number",
    "email", "emergency_contact_name", "emergency_contact_phone",
    "blood_type", "insurance_provider", "insurance_number",
    "marital_status", "preferred_language", "nationality",
    "allergies", "last_visit_date", "created_at", "updated_at",
}

FHIR_PATIENT_COLUMNS = {
    "id", "full_name", "birth_date", "gender", "address",
    "telecom", "marital_status", "insurance_number", "nationality",
}

FHIR_PATIENT_HISTORY_COLUMNS = {
    "id", "patient_id", "full_name", "address", "telecom",
    "marital_status", "nationality", "valid_from", "valid_to",
}


@pytest.fixture(scope="module")
def con():
    if not DB_PATH.exists():
        pytest.skip("Database not initialised — run `python src/setup_db.py` first")
    connection = duckdb.connect(str(DB_PATH))
    yield connection
    connection.close()


def test_expected_tables_exist(con):
    tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Missing tables: {missing}"


def test_patient_schema(con):
    columns = {row[0] for row in con.execute("DESCRIBE patient").fetchall()}
    missing = PATIENT_COLUMNS - columns
    assert not missing, f"Missing columns in patient: {missing}"


def test_fhir_patient_schema(con):
    columns = {row[0] for row in con.execute("DESCRIBE fhir_patient").fetchall()}
    missing = FHIR_PATIENT_COLUMNS - columns
    assert not missing, f"Missing columns in fhir_patient: {missing}"


def test_fhir_patient_history_schema(con):
    columns = {row[0] for row in con.execute("DESCRIBE fhir_patient_history").fetchall()}
    missing = FHIR_PATIENT_HISTORY_COLUMNS - columns
    assert not missing, f"Missing columns in fhir_patient_history: {missing}"


def test_pipeline_control_has_entries(con):
    count = con.execute("SELECT COUNT(*) FROM pipeline_control").fetchone()[0]
    assert count >= 2, "pipeline_control should have at least 2 entries (one per mart table)"
