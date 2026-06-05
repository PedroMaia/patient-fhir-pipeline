# Patient FHIR Pipeline

End-to-end data pipeline that ingests patient records from a CSV file and transforms them into a FHIR-compliant `patient` resource tech challenge for the company promptly health.
Built with Python and SQL, using DuckDB as the local database and Prefect for workflow orchestration.

## Overview

```
patient_data.csv  ──▶  patient (raw)  ──▶  fhir_patient         (marts)
                       ingestion +         fhir_patient_history  (marts)
                       validation          SQL transformation
```

Three stages:

1. **Schema setup** — creates `patient` and `fhir_patient` tables from DDL files.
2. **Ingestion** — reads the CSV, validates each row (email format, required dates, missing address), and loads valid rows into `patient`.
3. **Transformation** — derives `fhir_patient` (current state) and `fhir_patient_history` (full SCD2 history) from patient.

A fourth stage — **Data quality** — runs automatically after transformation: a YAML-driven runner (`init_data_tests.py`) validates the loaded data against a declarative spec (`docs/assets.yaml`), and is fully integrated into both Prefect and the pytest suite.

The pipeline follows a two-layer architecture: raw and mart.
The raw layer (patient) holds data as ingested from the CSV, with only structural validation applied (email format, required fields).
The mart layer (fhir_patient, fhir_patient_history) contains the final FHIR-compliant representation, ready for downstream consumption.
An **intermediate layer was omitted as the transformation logic is simple enough to go directly** from raw to mart in a single SQL step.
## Prerequisites

- Python 3.9 or higher
- macOS, Linux, or Windows
- No database server required — DuckDB runs embedded as a single file

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/PedroMaia/patient-fhir-pipeline
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

### With Prefect (recommended)

End-to-end with task-level logging and observability:

```bash
PYTHONPATH=src python src/pipeline_flow.py
```

Prefect starts a temporary local server automatically and runs all four stages (schema setup → ingestion → transformation → data quality). Each stage is a separate task with its own log stream.

To open the Prefect UI and keep a persistent run history, start the server in a separate terminal first:

```bash
# Terminal 1 — start the Prefect server
prefect server start

# Terminal 2 — run the pipeline (connects to the running server)
PYTHONPATH=src python src/pipeline_flow.py
```

Then open [http://localhost:4200](http://localhost:4200) to see flow runs, task states, logs, and timing.

### Without Prefect (legacy)

```bash
PYTHONPATH=src python src/run_pipeline.py
```

This delegates directly to `pipeline_flow.py` and produces the same result.

To run stages individually (plain Python, no orchestration):

```bash
PYTHONPATH=src python src/setup_db.py     # create tables
PYTHONPATH=src python src/ingest.py       # load CSV into patient
PYTHONPATH=src python src/transform.py    # transform patient -> fhir_patient
```

To run all tests (schema, connectivity, and data quality):

```bash
python -m pytest -v
```
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
│   ├── init_data_tests.py            # YAML-driven data quality runner
│   ├── pipeline_flow.py              # Prefect flow — main entry point
│   └── run_pipeline.py               # Legacy shim → delegates to pipeline_flow.py
├── tests/
│   ├── test_db.py                    # Environment and DuckDB connectivity tests
│   ├── check_schema_test.py          # Table and column schema tests
│   └── test_data_quality.py          # YAML-driven data quality tests (assets.yaml)
├── .env.example                      # Template for environment variables
├── prefect.yaml                      # Prefect deployment configuration
├── pyproject.toml                    # pytest configuration
└── requirements.txt
```

### Orchestration (Prefect)

The pipeline is orchestrated with [Prefect 3](https://docs.prefect.io/v3/). The entry point is [src/pipeline_flow.py](src/pipeline_flow.py), which defines:

| Prefect task | Maps to | Retries |
|---|---|---|
| `Schema Setup` | `setup_db.main()` | 1 (5 s delay) |
| `Ingest Patients` | `ingest.main()` | 2 (10 s delay) |
| `Transform to FHIR` | `transform.main()` | — |
| `Data Quality Tests` | `init_data_tests.run_all_tests()` | — |

Tasks run sequentially (each stage depends on the previous). If a task fails it is retried automatically; if it exhausts retries, the flow is marked as `Failed` and downstream tasks do not run.

**Logging** — each module exposes a `_get_logger()` helper that returns `get_run_logger()` from Prefect when called inside a task, or the standard Python logger when called from pytest or standalone scripts. This keeps modules framework-agnostic while routing all logs through Prefect's UI when the flow is running.

**Deployment** — `prefect.yaml` declares two deployments:

- `dev` — run on demand, no schedule
- `daily` — cron `0 6 * * *` (Europe/Lisbon), disabled by default

To register deployments with the server:

```bash
prefect deploy
```

To trigger a run from the CLI:

```bash
prefect deployment run 'Patient FHIR Pipeline/dev'
```

### Pipeline control

Each target table has a configurable load strategy stored in the `pipeline_control` table:

| Table                  | Strategy         | Behaviour                                      |
|------------------------|------------------|------------------------------------------------|
| `fhir_patient`         | `merge`  | Upsert — only updates rows that changed        |
| `fhir_patient_history` | `merge`  | Inserts new versions, updates valid_to only    |

Supported strategies:

- **`merge`** — uses SQL `MERGE`. Only touches rows that actually changed (`IS DISTINCT FROM`). Safe for production — preserves FK integrity and is idempotent.
- **`truncate_insert`** — deletes all rows and reinserts. Simpler but destructive. Note: due to a DuckDB FK constraint limitation, `truncate_insert` on `fhir_patient` requires wrapping both tables in the same delete sequence.

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

### Validation and rejection

Rows are validated before insertion. A row is rejected (with logged reason) if:

- `email` is missing or doesn't match a standard email pattern
- `birth_date` is missing or not parseable as `YYYY-MM-DD`
- `address` is missing

Empty strings in `allergies` are normalized to `NULL`. Invalid `last_visit_date` values are silently converted to `NULL` (the field is non-critical and patients may have no recorded visits).

## Database inspection

Open an interactive session:
```bash
duckdb db/patient.duckdb
```

Or run a single query directly:
```bash
duckdb db/patient.duckdb "<query>"
```

### Useful commands

```bash
# Show all tables
duckdb db/patient.duckdb "SHOW TABLES;"

# Count rows per table
duckdb db/patient.duckdb "SELECT COUNT(*) AS total FROM patient;"
duckdb db/patient.duckdb "SELECT COUNT(*) AS total FROM fhir_patient;"
duckdb db/patient.duckdb "SELECT COUNT(*) AS total FROM fhir_patient_history;"

# Preview data
duckdb db/patient.duckdb "SELECT * FROM patient LIMIT 5;"
duckdb db/patient.duckdb "SELECT * FROM fhir_patient LIMIT 5;"
duckdb db/patient.duckdb "SELECT * FROM fhir_patient_history LIMIT 5;"

# Check pipeline_control strategies
duckdb db/patient.duckdb "SELECT * FROM pipeline_control;"

# Check for duplicate insurance_number in fhir_patient
duckdb db/patient.duckdb "SELECT insurance_number, COUNT(*) FROM fhir_patient GROUP BY insurance_number HAVING COUNT(*) > 1;"

# Full history of a specific patient
duckdb db/patient.duckdb "SELECT * FROM fhir_patient_history WHERE patient_id = MD5('AR-20910') ORDER BY valid_from;"

# Current state of a specific patient
duckdb db/patient.duckdb "SELECT * FROM fhir_patient WHERE insurance_number = 'AR-20910';"

# Current records in history (valid_to IS NULL)
duckdb db/patient.duckdb "SELECT * FROM fhir_patient_history WHERE valid_to IS NULL ORDER BY valid_from;"
```

> **Note:** DuckDB allows only one writer at a time. Close any open CLI or DBeaver sessions before running the pipeline.

## Tests

The test suite is split into three files, all run with a single command:

```bash
python -m pytest -v
```

### Test files

| File | What it tests |
|------|---------------|
| `tests/test_db.py` | Environment configuration (`DB_PATH`, `CSV_PATH`) and DuckDB connectivity |
| `tests/check_schema_test.py` | All expected tables exist and each table has the correct columns |
| `tests/test_data_quality.py` | Data quality assertions from `docs/assets.yaml` — one test node per assertion |

The schema and data quality tests require the pipeline to have been initialised first. If the database does not exist, those tests are automatically skipped with a clear message.

### Data quality tests

`docs/assets.yaml` declares quality assertions per column in a dbt-inspired format:

```yaml
- name: email
  description: Patient email, validated on ingestion
  tests: [not_null, valid_email]
```

`tests/test_data_quality.py` reads this file at collection time and generates one pytest node per `(table, column, test)` triple, so the output clearly identifies exactly which assertion failed:

```
tests/test_data_quality.py::test_data_quality[patient.email.not_null] PASSED
tests/test_data_quality.py::test_data_quality[patient.email.valid_email] PASSED
tests/test_data_quality.py::test_data_quality[fhir_patient.id.unique] PASSED
...
```

Supported test types:

| Test | Validates |
|------|-----------|
| `not_null` | Column has no NULL values |
| `unique` | Column has no duplicate non-null values |
| `accepted_values` | All non-null values belong to a specified set |
| `valid_email` | All non-null values match a standard email pattern |

To run only the data quality tests:

```bash
python -m pytest -v tests/test_data_quality.py
```

The suite exits with code `1` if any assertion fails, making it suitable for CI integration.

## Future improvements
- Replace DuckDB with Postgres in production; the transformation SQL is portable with minor syntax adjustments.
- Implement dbt for the transformation layer.
- Enable the `daily` Prefect deployment and connect to Prefect Cloud for centralised run history across environments.