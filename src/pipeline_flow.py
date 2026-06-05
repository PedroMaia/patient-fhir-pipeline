"""Patient FHIR Pipeline — Prefect flow entry point."""
from prefect import flow, task, get_run_logger

import setup_db
import ingest
import transform
import init_data_tests


@task(name="Schema Setup", retries=1, retry_delay_seconds=5)
def setup_schema():
    log = get_run_logger()
    log.info("Setting up database schema...")
    setup_db.main()


@task(name="Ingest Patients", retries=2, retry_delay_seconds=10)
def ingest_patients():
    log = get_run_logger()
    log.info("Starting CSV ingestion...")
    ingest.main()


@task(name="Transform to FHIR")
def transform_fhir():
    log = get_run_logger()
    log.info("Starting FHIR transformation...")
    transform.main()


@task(name="Data Quality Tests")
def data_quality():
    results = init_data_tests.run_all_tests()
    exit_code = init_data_tests.print_summary(results)
    if exit_code != 0:
        failed_count = sum(1 for r in results if not r.passed)
        raise RuntimeError(f"{failed_count} data quality test(s) failed — check logs above")


@flow(name="Patient FHIR Pipeline", log_prints=True)
def patient_fhir_pipeline():
    setup_schema()
    ingest_patients()
    transform_fhir()
    data_quality()


if __name__ == "__main__":
    patient_fhir_pipeline()
