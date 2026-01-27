import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from validators.range import RangeValidator


def test_range_validator_out_of_bounds():
    validator = RangeValidator({"rate": (-0.04, 0.04)})
    rows = [{"rate": 0.01}, {"rate": 0.1}]
    report = validator.validate(rows)
    assert report.error_count == 1
