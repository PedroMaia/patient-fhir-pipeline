"""Runs data quality tests defined in docs/assets.yaml against DuckDB."""
import logging
import sys
from dataclasses import dataclass
from typing import Any, Callable

import yaml

from src.config import PROJECT_ROOT, LOG_LEVEL
from db import get_connection

logging.basicConfig(level=LOG_LEVEL, format="%(message)s")
log = logging.getLogger(__name__)

YAML_PATH = PROJECT_ROOT / "docs" / "assets.yaml"

# Simplified regex for email validation (same as ingestion)
EMAIL_REGEX = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"


# =============================================================================
# Test result types
# =============================================================================
@dataclass
class TestResult:
    asset: str
    column: str
    test_name: str
    passed: bool
    violations: int = 0
    example_query: str = ""


# =============================================================================
# SQL builders — one per test type
# =============================================================================
def sql_not_null(table: str, column: str, _params: Any = None) -> str:
    return f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL"


def sql_unique(table: str, column: str, _params: Any = None) -> str:
    return f"""
        SELECT COUNT(*) FROM (
            SELECT {column}
            FROM {table}
            WHERE {column} IS NOT NULL
            GROUP BY {column}
            HAVING COUNT(*) > 1
        )
    """


def sql_accepted_values(table: str, column: str, values: list) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"""
        SELECT COUNT(*) FROM {table}
        WHERE {column} IS NOT NULL
          AND {column} NOT IN ({quoted})
    """


def sql_valid_email(table: str, column: str, _params: Any = None) -> str:
    return f"""
        SELECT COUNT(*) FROM {table}
        WHERE {column} IS NOT NULL
          AND NOT regexp_matches({column}, '{EMAIL_REGEX}')
    """


# Registry: test name -> SQL builder function
TEST_BUILDERS: dict[str, Callable] = {
    "not_null": sql_not_null,
    "unique": sql_unique,
    "accepted_values": sql_accepted_values,
    "valid_email": sql_valid_email,
}


# =============================================================================
# Test runner
# =============================================================================
def parse_test(test_def: Any) -> tuple[str, Any]:
    """
    Normalizes a test definition into (test_name, params).
    Supports:
      - 'not_null'                          -> ('not_null', None)
      - {'accepted_values': [...]}          -> ('accepted_values', [...])
    """
    if isinstance(test_def, str):
        return test_def, None
    if isinstance(test_def, dict):
        name = next(iter(test_def))
        return name, test_def[name]
    raise ValueError(f"Invalid test definition: {test_def}")


def run_test(con, asset: str, column: str, test_def: Any) -> TestResult:
    test_name, params = parse_test(test_def)

    builder = TEST_BUILDERS.get(test_name)
    if builder is None:
        log.warning(f"Unknown test '{test_name}' — skipping")
        return TestResult(asset, column, test_name, passed=False,
                          violations=-1, example_query="<unknown test>")

    query = builder(asset, column, params)
    violations = con.execute(query).fetchone()[0]

    return TestResult(
        asset=asset,
        column=column,
        test_name=test_name,
        passed=(violations == 0),
        violations=violations,
        example_query=query.strip(),
    )


def run_all_tests() -> list[TestResult]:
    log.info(f"Loading {YAML_PATH.relative_to(PROJECT_ROOT)}")
    config = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))

    results: list[TestResult] = []

    with get_connection() as con:
        for asset in config.get("assets", []):
            asset_name = asset["name"]
            log.info(f"\nRunning tests for asset: {asset_name}")

            for column in asset.get("columns", []):
                col_name = column["name"]
                tests = column.get("tests", [])

                for test_def in tests:
                    result = run_test(con, asset_name, col_name, test_def)
                    results.append(result)

                    status = "PASS" if result.passed else "FAIL"
                    line = f"  {status} | {asset_name}.{col_name} | {result.test_name}"
                    if not result.passed:
                        line += f" | {result.violations} violations"
                    log.info(line)

    return results


def print_summary(results: list[TestResult]) -> int:
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    log.info("\n" + "=" * 60)
    log.info(f"Summary: {passed} passed, {failed} failed")
    log.info("=" * 60)

    if failed > 0:
        log.info("\nFailed tests detail:")
        for r in results:
            if not r.passed:
                log.info(f"\n  {r.asset}.{r.column} | {r.test_name}")
                log.info(f"  Violations: {r.violations}")
                log.info(f"  Query: {r.example_query}")

    return 0 if failed == 0 else 1


def main() -> None:
    results = run_all_tests()
    exit_code = print_summary(results)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()