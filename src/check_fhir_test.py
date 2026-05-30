"""Inspect the transformed FHIR patient table."""
from db import get_connection

with get_connection() as con:
    print("Schema:")
    print(con.execute("DESCRIBE fhir_patient").fetchdf())

    print("\nFirst 5 rows:")
    print(con.execute("""
        SELECT id, full_name, birth_date, telecom, nationality
        FROM fhir_patient
        LIMIT 5
    """).fetchdf())

    print("\nTelecom field as JSON:")
    print(con.execute("""
        SELECT
            full_name,
            telecom->>'$.phone' AS phone,
            telecom->>'$.email' AS email
        FROM fhir_patient
        LIMIT 3
    """).fetchdf())