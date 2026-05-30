-- FHIR-compliant patient table
-- Adapted from Postgres DDL:
--   JSONB     -> JSON  (DuckDB doesn't have JSONB, only JSON)
--   VARCHAR(n) -> VARCHAR (length ignored in DuckDB)

CREATE TABLE IF NOT EXISTS fhir_patient (
    id                VARCHAR PRIMARY KEY,
    full_name         VARCHAR,
    birth_date        DATE,
    gender            VARCHAR,
    address           VARCHAR,
    telecom           JSON,
    marital_status    VARCHAR,
    insurance_number  VARCHAR,
    nationality       VARCHAR
);