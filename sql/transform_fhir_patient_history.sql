-- -----------------------------------------------------------------------------
-- 2. fhir_patient_history (SCD2 — todas as versões)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fhir_patient_history (
    id              VARCHAR(255) PRIMARY KEY,
    patient_id      VARCHAR(255) REFERENCES fhir_patient(id),
    full_name       VARCHAR(200),
    address         VARCHAR(255),
    telecom         JSON,
    marital_status  VARCHAR(20),
    nationality     VARCHAR(20),
    valid_from      DATE NOT NULL,
    valid_to        DATE
);

INSERT INTO fhir_patient_history (
    id,
    patient_id,
    full_name,
    address,
    telecom,
    marital_status,
    nationality,
    valid_from,
    valid_to
)
SELECT
    MD5(insurance_number || last_visit_date::VARCHAR)   AS id,
    MD5(insurance_number)                               AS patient_id,
    CONCAT_WS(' ', first_name, last_name)               AS full_name,
    address,
    json_object(
        'phone', phone_number,
        'email', email
    )                                                  AS telecom,
    marital_status,
    SUBSTRING(nationality, 1, 20)                       AS nationality,
    last_visit_date                                     AS valid_from,
    LEAD(last_visit_date) OVER (
        PARTITION BY insurance_number
        ORDER BY last_visit_date
    )                                                   AS valid_to
FROM patient
ON CONFLICT (id) DO NOTHING;