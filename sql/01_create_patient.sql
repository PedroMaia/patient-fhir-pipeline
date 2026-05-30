-- Source table: raw patient data ingested from CSV
-- Adapted from Postgres DDL:
--   SERIAL          -> SEQUENCE + DEFAULT nextval()
--   VARCHAR(n)      -> VARCHAR (DuckDB ignores length, kept as docs)
--   TIMESTAMP WITH TIME ZONE -> TIMESTAMPTZ

CREATE SEQUENCE IF NOT EXISTS patient_id_seq;

CREATE TABLE IF NOT EXISTS patient (
    id                      INTEGER PRIMARY KEY DEFAULT nextval('patient_id_seq'),
    first_name              VARCHAR,
    last_name               VARCHAR,
    birth_date              DATE,
    gender                  VARCHAR,
    address                 VARCHAR,
    city                    VARCHAR,
    state                   VARCHAR,
    zip_code                VARCHAR,
    phone_number            VARCHAR,
    email                   VARCHAR,
    emergency_contact_name  VARCHAR,
    emergency_contact_phone VARCHAR,
    blood_type              VARCHAR,
    insurance_provider      VARCHAR,
    insurance_number        VARCHAR,
    marital_status          VARCHAR,
    preferred_language      VARCHAR,
    nationality             VARCHAR,
    allergies               TEXT,
    last_visit_date         DATE,
    created_at              TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);