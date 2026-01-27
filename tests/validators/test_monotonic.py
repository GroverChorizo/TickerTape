import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from validators.monotonic import MonotonicValidator


def test_monotonic_validator_detects_out_of_order():
    validator = MonotonicValidator("ts", strict=True)
    rows = [{"ts": 1}, {"ts": 2}, {"ts": 2}]
    report = validator.validate(rows)
    assert report.error_count == 1
