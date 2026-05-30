"""End-to-end pipeline: schema -> ingest -> transform."""
import logging

from config import LOG_LEVEL
import setup_db
import ingest
import transform

logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    log.info("=" * 60)
    log.info("STEP 1/3: Schema setup")
    log.info("=" * 60)
    setup_db.main()

    log.info("=" * 60)
    log.info("STEP 2/3: Ingestion")
    log.info("=" * 60)
    ingest.main()

    log.info("=" * 60)
    log.info("STEP 3/3: FHIR transformation")
    log.info("=" * 60)
    transform.main()

    log.info("Pipeline complete.")


if __name__ == "__main__":
    main()