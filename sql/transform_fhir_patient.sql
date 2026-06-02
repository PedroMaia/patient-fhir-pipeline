-- =============================================================================
-- Transform: patient -> fhir_patient + fhir_patient_history
-- =============================================================================
-- Decisions:
--   - fhir_patient: always holds the most recent state per patient.
--   - fhir_patient_history: SCD2 — one row per change, valid_from/valid_to.
--   - id: MD5(insurance_number) — stable across visits.
--   - history.id: MD5(insurance_number || last_visit_date) — unique per version.
--   - valid_to NULL means current record.
--   - telecom: JSON object with phone and email.
--   - nationality: truncated to 20 chars (see README for ISO 3166 note).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. fhir_patient (estado mais recente)
-- -----------------------------------------------------------------------------
INSERT INTO fhir_patient (
    id,
    full_name,
    birth_date,
    gender,
    address,
    telecom,
    marital_status,
    insurance_number,
    nationality
)
SELECT DISTINCT ON (insurance_number)
    MD5(insurance_number)                               AS id,
    CONCAT_WS(' ', first_name, last_name)               AS full_name,
    birth_date,
    gender,
    address,
    json_object(
        'phone', phone_number,
        'email', email
    )                                                   AS telecom,
    marital_status,
    insurance_number,
    SUBSTRING(nationality, 1, 20)                       AS nationality
FROM patient
ORDER BY insurance_number, last_visit_date DESC
ON CONFLICT (id) DO UPDATE SET
    full_name        = EXCLUDED.full_name,
    birth_date       = EXCLUDED.birth_date,
    gender           = EXCLUDED.gender,
    address          = EXCLUDED.address,
    telecom          = EXCLUDED.telecom,
    marital_status   = EXCLUDED.marital_status,
    nationality      = EXCLUDED.nationality;