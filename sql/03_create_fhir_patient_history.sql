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