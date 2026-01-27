import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from validators.missingness import MissingnessValidator


def test_missingness_validator_threshold():
    validator = MissingnessValidator(fields=["price"], max_missing_ratio=0.25)
    rows = [{"price": 1}, {"price": None}, {"price": None}, {"price": 4}]
    report = validator.validate(rows)
    assert report.error_count == 1
