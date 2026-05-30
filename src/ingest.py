"""Ingests patient_data.csv into the patient table."""
import logging

import duckdb
import pandas as pd

from config import CSV_PATH, DB_PATH, LOG_LEVEL, PROJECT_ROOT
from db import get_connection
from db import run_sql_file
from validation import is_valid_email, is_valid_date, clean_string

logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# Columns expected in the CSV, in the order the patient table receives them
CSV_COLUMNS = [
    "first_name", "last_name", "birth_date", "gender", "address",
    "city", "state", "zip_code", "phone_number", "email",
    "emergency_contact_name", "emergency_contact_phone", "blood_type",
    "insurance_provider", "insurance_number", "marital_status",
    "preferred_language", "nationality", "allergies", "last_visit_date",
]


def load_csv(path) -> pd.DataFrame:
    """Reads the CSV into a DataFrame, with strings instead of NaN."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
    log.info(f"Loaded {len(df)} rows from {path}")
    return df


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Applies cleaning rules to the raw DataFrame."""
    # Normalize whitespace and empty strings to NaN/None across all string cols
    for col in df.columns:
        df[col] = df[col].apply(clean_string)
    return df


def validate_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Splits rows into (valid, rejected) based on validation rules:
      - email must be valid format (bonus task)
      - birth_date must not be missing (bonus task)
      - address must not be missing (bonus task)
    Returns two DataFrames: rows to insert, rows rejected with a reason.
    """
    df = df.copy()

    invalid_email = ~df["email"].apply(is_valid_email)
    missing_birth = ~df["birth_date"].apply(is_valid_date)
    missing_address = df["address"].isna()

    reasons = []
    for i in range(len(df)):
        row_reasons = []
        if invalid_email.iloc[i]:
            row_reasons.append("invalid_email")
        if missing_birth.iloc[i]:
            row_reasons.append("missing_birth_date")
        if missing_address.iloc[i]:
            row_reasons.append("missing_address")
        reasons.append(",".join(row_reasons) if row_reasons else None)

    df["_reject_reason"] = reasons
    rejected = df[df["_reject_reason"].notna()].copy()
    valid = df[df["_reject_reason"].isna()].drop(columns=["_reject_reason"])

    if len(rejected) > 0:
        log.warning(f"Rejected {len(rejected)} rows:")
        for _, r in rejected.iterrows():
            log.warning(
                f"  {r['first_name']} {r['last_name']}: {r['_reject_reason']}"
            )
    else:
        log.info("All rows passed validation")

    return valid, rejected


def insert_patients(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """Inserts the DataFrame into the patient table. Returns rows inserted."""
    if df.empty:
        log.warning("No rows to insert")
        return 0

    # Register the DataFrame as a virtual table so DuckDB can read it directly
    con.register("df_patients", df[CSV_COLUMNS])

    columns_csv = ", ".join(CSV_COLUMNS)
    con.execute(f"""
        INSERT INTO patient ({columns_csv})
        SELECT {columns_csv} FROM df_patients
    """)

    con.unregister("df_patients")
    log.info(f"Inserted {len(df)} rows into patient")
    return len(df)


def main() -> None:
    log.info(f"Starting ingestion: {CSV_PATH} -> {DB_PATH}")

    df = load_csv(CSV_PATH)
    df = clean_dataframe(df)
    valid, rejected = validate_rows(df)

    with get_connection() as con:
        # Idempotency: clear the table before re-ingesting
        # Alternative: use ON CONFLICT if we had a natural key
        con.execute("DELETE FROM patient")
        con.execute("DROP SEQUENCE IF EXISTS patient_id_seq")
        run_sql_file(PROJECT_ROOT / "sql" / "01_create_patient.sql")

        with get_connection() as con:
            inserted = insert_patients(con, valid)  
    log.info(f"Done. Inserted: {inserted} | Rejected: {len(rejected)}")


if __name__ == "__main__":
    main()