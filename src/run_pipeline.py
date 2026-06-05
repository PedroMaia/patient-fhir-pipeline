"""Legacy entry point — delegates to the Prefect flow."""
from pipeline_flow import patient_fhir_pipeline

if __name__ == "__main__":
    patient_fhir_pipeline()
