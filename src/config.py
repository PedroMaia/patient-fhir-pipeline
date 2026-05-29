"""Loads environment variables from .env file."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Project root = parent of src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

DB_PATH = PROJECT_ROOT / os.getenv("DB_PATH", "./db/patient.duckdb").lstrip("./")
CSV_PATH = PROJECT_ROOT / os.getenv("CSV_PATH", "./data/patient_data.csv").lstrip("./")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")