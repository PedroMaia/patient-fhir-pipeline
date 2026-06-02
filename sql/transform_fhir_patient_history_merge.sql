-- =============================================================================
-- Transform: patient -> fhir_patient_history (MERGE strategy)
-- =============================================================================
-- Decisions:
--   - MERGE inserts new versions, updates valid_to if it changed.
--   - History rows are never deleted — only valid_to is updated when
--     a newer visit supersedes a record.
--   - id: MD5(insurance_number || last_visit_date) — unique per version.
--   - valid_to NULL means current record.
-- =============================================================================

MERGE INTO fhir_patient_history AS target
USING (
    SELECT
        MD5(insurance_number || last_visit_date::VARCHAR)   AS id,
        MD5(insurance_number)                               AS patient_id,
        CONCAT_WS(' ', first_name, last_name)               AS full_name,
        address,
        json_object(
            'phone', phone_number,
            'email', email
        )                                                   AS telecom,
        marital_status,
        SUBSTRING(nationality, 1, 20)                       AS nationality,
        last_visit_date                                     AS valid_from,
        LEAD(last_visit_date) OVER (
            PARTITION BY insurance_number
            ORDER BY last_visit_date
        )                                                   AS valid_to
    FROM patient
) AS source ON target.id = source.id
WHEN MATCHED AND (
    target.valid_to IS DISTINCT FROM source.valid_to
) THEN UPDATE SET
    valid_to = source.valid_to
WHEN NOT MATCHED THEN INSERT (
    id, patient_id, full_name, address, telecom, marital_status, nationality, valid_from, valid_to
) VALUES (
    source.id, source.patient_id, source.full_name, source.address,
    source.telecom, source.marital_status, source.nationality, source.valid_from, source.valid_to
);