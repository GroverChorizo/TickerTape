import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from validators.schema import SchemaValidator


def test_schema_validator_missing_and_type():
    validator = SchemaValidator(
        required={"ts": int, "symbol": str}, optional={"size": float}
    )
    rows = [
        {"ts": 1, "symbol": "BTC", "size": 1.0},
        {"ts": None, "symbol": "ETH"},
        {"ts": 2, "symbol": 3},
    ]
    report = validator.validate(rows)
    assert report.error_count == 2
    assert report.warning_count == 0


def test_schema_validator_optional_type_warning():
    validator = SchemaValidator(required={"ts": int}, optional={"size": float})
    rows = [{"ts": 1, "size": "bad"}]
    report = validator.validate(rows)
    assert report.error_count == 0
    assert report.warning_count == 1
