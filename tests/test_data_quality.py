"""Data quality tests driven by docs/assets.yaml — one test node per assertion."""
import duckdb
import pytest
import yaml

from config import DB_PATH, PROJECT_ROOT
from init_data_tests import parse_test, run_test

YAML_PATH = PROJECT_ROOT / "docs" / "assets.yaml"


def _collect_cases():
    """Parse assets.yaml and return one pytest.param per (asset, column, test) triple."""
    config = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    cases = []
    for asset in config.get("assets", []):
        for column in asset.get("columns", []):
            for test_def in column.get("tests", []):
                test_name, _ = parse_test(test_def)
                cases.append(
                    pytest.param(
                        asset["name"],
                        column["name"],
                        test_def,
                        id=f"{asset['name']}.{column['name']}.{test_name}",
                    )
                )
    return cases


@pytest.fixture(scope="module")
def con():
    if not DB_PATH.exists():
        pytest.skip("Database not initialised — run `python src/setup_db.py` first")
    connection = duckdb.connect(str(DB_PATH))
    yield connection
    connection.close()


@pytest.mark.parametrize("asset,column,test_def", _collect_cases())
def test_data_quality(con, asset, column, test_def):
    result = run_test(con, asset, column, test_def)
    assert result.passed, (
        f"{result.violations} violation(s) in {asset}.{column} [{result.test_name}]\n"
        f"Query: {result.example_query}"
    )
