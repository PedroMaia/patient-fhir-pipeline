# Patient FHIR Pipeline

End-to-end data pipeline that ingests patient records from a CSV file and transforms them into a FHIR-compliant `patient` resource table.
Built with Python and SQL, using DuckDB as the local database.

## Overview

```
patient_data.csv  ──▶  patient (raw)  ──▶  fhir_patient         (estado atual)
                       ingestion +         fhir_patient_history  (SCD2 histórico)
                       validation          SQL transformation
```

Three stages:

1. **Schema setup** — creates `patient` and `fhir_patient` tables from DDL files.
2. **Ingestion** — reads the CSV, validates each row (email format, required dates, missing address), and loads valid rows into `patient`.
3. **Transformation** — derives `fhir_patient` (current state) and `fhir_patient_history` (full SCD2 history) from patient.

A YAML-driven data quality runner (`data_tests.py`) validates the loaded data against a declarative spec (`docs/assets.yaml`).


## Prerequisites

- Python 3.9 or higher
- macOS, Linux, or Windows
- No database server required — DuckDB runs embedded as a single file

## Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd patient-fhir-pipeline

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\Activate.ps1       # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
```

The `.env` file defines paths for the database and the CSV. Default values work out of the box.

## Running the pipeline

End-to-end with one command:

```bash
python src/run_pipeline.py
```

This runs schema setup, ingestion, and transformation in sequence.

To run stages individually:

```bash
python src/setup_db.py     # create tables
python src/ingest.py       # load CSV into patient
python src/transform.py    # transform patient -> fhir_patient
```

To run data quality tests defined in `docs/assets.yaml`:

```bash
python src/data_tests.py
```

The data tests exit with code `1` if any check fails, making them suitable for CI integration.

## Project structure

```
patient-fhir-pipeline/
├── data/
│   └── patient_data.csv              # Source CSV
├── db/
│   └── patient.duckdb                # DuckDB file (gitignored)
├── docs/
│   └── assets.yaml                   # Data asset documentation + test specs
├── sql/
│   ├── 01_create_patient.sql
│   ├── 02_create_fhir_patient.sql
│   ├── 03_create_fhir_patient_history.sql
│   ├── 04_create_pipeline_control.sql
│   ├── transform_fhir_patient.sql
│   ├── transform_fhir_patient_merge.sql
│   ├── transform_fhir_patient_history.sql
│   └── transform_fhir_patient_history_merge.sql
├── src/
│   ├── config.py                     # Env-driven configuration
│   ├── db.py                         # DuckDB connection helper
│   ├── validation.py                 # Email and date validators
│   ├── setup_db.py                   # Applies DDL files
│   ├── ingest.py                     # CSV ingestion
│   ├── transform.py                  # Runs SQL transformation
│   ├── data_tests.py                 # YAML-driven data quality runner
│   └── run_pipeline.py               # Orchestrates all stages
├── tests/                            # pytest tests for structural validation
├── .env.example                      # Template for environment variables
├── pyproject.toml                    # pytest configuration
└── requirements.txt
```

### Pipeline control

Each target table has a configurable load strategy stored in the `pipeline_control` table:

| Table                  | Strategy         | Behaviour                                      |
|------------------------|------------------|------------------------------------------------|
| `fhir_patient`         | `merge`          | Upsert — only updates rows that changed        |
| `fhir_patient_history` | `merge`          | Inserts new versions, updates valid_to only    |

Supported strategies:

- **`merge`** — uses SQL `MERGE`. Only touches rows that actually changed (`IS DISTINCT FROM`). Safe for production — preserves FK integrity and is idempotent.
- **`truncate_insert`** — deletes all rows and reinserts. Simpler but destructive. Note: due to a DuckDB FK constraint limitation, `truncate_insert` on `fhir_patient` requires wrapping both tables in the same delete sequence. Not recommended when FK relationships exist.

To change strategy at runtime without redeploying:

    UPDATE pipeline_control SET strategy = 'truncate_insert' WHERE table_name = 'fhir_patient';

## Design decisions

### DuckDB instead of Postgres

The exercise provides Postgres-flavored DDL but explicitly allows any tool. DuckDB was chosen for **zero-setup reproducibility** — the entire pipeline runs with `pip install` and one command, with no database server to configure. The transformation logic is portable to Postgres with minimal changes.

DDL adaptations from the original DDL specification:

| DDL | DuckDB | Notes |
|---|---|---|
| `SERIAL` | `SEQUENCE` + `DEFAULT nextval()` | Functionally equivalent |
| `JSONB` | `JSON` | DuckDB's `JSON` uses binary storage internally, equivalent to DDL `JSONB` in practice |
| `VARCHAR(n)` | `VARCHAR` | Length is not enforced in DuckDB; truncation handled in transformation SQL where needed |
| `TIMESTAMP WITH TIME ZONE` | `TIMESTAMPTZ` | Direct equivalent |

### Deterministic FHIR `id`
The fhir_patient.id is generated as MD5(insurance_number) — stable across visits.
The fhir_patient_history.id is generated as MD5(insurance_number || last_visit_date) — unique per version.

- **Deterministic** — same input always produces the same `id`
- **Idempotent** — combined with `INSERT OR REPLACE`, running the transformation multiple times yields the same result
- **Reproducible** — useful for downstream systems that reference patients by `id`

### Patient history — SCD2

fhir_patient always holds the most recent demographic state per patient (1 row per patient).
fhir_patient_history tracks every change over time using a Slowly Changing Dimension Type 2 pattern:

- valid_from: the visit date when this version became active
- valid_to: the visit date when it was superseded (NULL = current record)
- Fields tracked: address, telecom, marital_status, nationality

Fields excluded from history (immutable): full_name, birth_date, gender, insurance_number.

To query the full history of a patient:

    SELECT * FROM fhir_patient_history
    WHERE patient_id = MD5('AR-20910')
    ORDER BY valid_from;

To get the state of a patient at a specific date:

    SELECT * FROM fhir_patient_history
    WHERE patient_id = MD5('AR-20910')
      AND '2023-06-15' BETWEEN valid_from AND COALESCE(valid_to, CURRENT_DATE);

### Idempotent ingestion

DuckDB does not yet support `ALTER SEQUENCE ... RESTART`. Idempotency is achieved by dropping and recreating the `patient` table at the start of each ingestion run. In a Postgres deployment this would be replaced by `TRUNCATE patient RESTART IDENTITY`.

### Validation and rejection

Rows are validated before insertion. A row is rejected (with logged reason) if:

- `email` is missing or doesn't match a standard email pattern
- `birth_date` is missing or not parseable as `YYYY-MM-DD`
- `address` is missing

Empty strings in `allergies` are normalized to `NULL`. Invalid `last_visit_date` values are silently converted to `NULL` (the field is non-critical and patients may have no recorded visits).

### Nationality truncation

The source schema has `nationality VARCHAR(100)` and the FHIR target has `VARCHAR(20)`. The transformation explicitly truncates with `SUBSTRING(nationality, 1, 20)`. In a real FHIR system this field would map to an ISO 3166 country code (e.g., `"American"` → `"US"`); that mapping is out of scope here.

## Data quality tests

`docs/assets.yaml` documents both tables column-by-column and declares quality tests in a dbt-inspired format:

```yaml
- name: email
  description: Patient email, validated on ingestion
  tests: [not_null, valid_email]
```

Supported test types:

| Test | Validates |
|---|---|
| `not_null` | Column has no NULL values |
| `unique` | Column has no duplicate non-null values |
| `accepted_values` | All values are in a specified set |
| `valid_email` | All values match an email regex |

`src/data_tests.py` loads the YAML, generates SQL queries per test, runs them against DuckDB, and reports pass/fail with violation counts.

## Running tests

```bash
# Data quality tests (YAML-driven)
python src/data_tests.py

# Structural tests (pytest)
pytest -v
```

## Troubleshooting

**`ModuleNotFoundError` when running scripts** — Make sure the virtual environment is active (`source .venv/bin/activate`) and that you're running scripts as shown above.

**DuckDB lock errors** — DuckDB allows only one writer at a time. Close any open connections (notebooks, DBeaver, CLI sessions) before running the pipeline.

**Validation rejects rows unexpectedly** — Check the logs for the rejection reason. The validators in `src/validation.py` can be tightened or relaxed as needed.

## Future improvements
- Change the primarykey to insurance_number;(DONE)
- Migrate fhir_patient_history to a MERGE-based upsert to avoid delete/insert on re-runs.(DONE)
- Replace DuckDB with Postgres in production; the transformation SQL is portable with minor syntax adjustments.
- Add orchestration with Prefect to schedule and monitor pipeline runs, with task-level retries and observability via the Prefect UI. 