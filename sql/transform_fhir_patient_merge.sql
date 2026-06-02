-- =============================================================================
-- Transform: patient -> fhir_patient (MERGE strategy)
-- =============================================================================
-- Decisions:
--   - MERGE only touches rows that actually changed (IS DISTINCT FROM).
--   - Immutable fields (birth_date, gender) are not updated on MATCH.
--   - id: MD5(insurance_number) — stable across visits.
--   - telecom: JSON object with phone and email.
--   - nationality: truncated to 20 chars (see README for ISO 3166 note).
-- =============================================================================

MERGE INTO fhir_patient AS target
USING (
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
) AS source ON target.id = source.id
WHEN MATCHED AND (
    target.address        IS DISTINCT FROM source.address        OR
    target.marital_status IS DISTINCT FROM source.marital_status OR
    target.telecom        IS DISTINCT FROM source.telecom        OR
    target.nationality    IS DISTINCT FROM source.nationality    OR
    target.full_name      IS DISTINCT FROM source.full_name
) THEN UPDATE SET
    full_name      = source.full_name,
    address        = source.address,
    telecom        = source.telecom,
    marital_status = source.marital_status,
    nationality    = source.nationality
WHEN NOT MATCHED THEN INSERT (
    id, full_name, birth_date, gender, address, telecom, marital_status, insurance_number, nationality
) VALUES (
    source.id, source.full_name, source.birth_date, source.gender,
    source.address, source.telecom, source.marital_status, source.insurance_number, source.nationality
);