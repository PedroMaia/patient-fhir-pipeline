-- =============================================================================
-- Transform: patient -> fhir_patient
-- =============================================================================
-- Decisions:
--   - id: deterministic MD5 hash of (first_name, last_name, birth_date).
--         Reproducible across runs, idempotent with INSERT OR REPLACE.
--   - full_name: CONCAT_WS handles NULL gracefully (skips them).
--   - telecom: JSON object built from phone_number and email.
--   - nationality: source is VARCHAR(100), target is VARCHAR(20).
--         We truncate to 20 chars. In a real FHIR system this would
--         map to an ISO 3166 country code (e.g., "American" -> "US").
--         Out of scope here, documented in README.
-- =============================================================================

INSERT OR REPLACE INTO fhir_patient (
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
SELECT 
    MD5(insurance_number || last_visit_date::VARCHAR)   AS id,
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
FROM patient;