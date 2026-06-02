CREATE TABLE IF NOT EXISTS pipeline_control (
    table_name   VARCHAR PRIMARY KEY,
    strategy     VARCHAR CHECK (strategy IN ('merge', 'truncate_insert')),
    updated_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
--merge or truncate_insert
INSERT INTO pipeline_control (table_name, strategy) VALUES
    ('fhir_patient',         'truncate_insert'),
    ('fhir_patient_history', 'truncate_insert')
ON CONFLICT (table_name) DO NOTHING;