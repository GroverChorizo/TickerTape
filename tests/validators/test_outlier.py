import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from validators.outlier import OutlierValidator


def test_outlier_validator_flags():
    validator = OutlierValidator("value", z_threshold=1.5)
    rows = [{"value": 1}, {"value": 1}, {"value": 1}, {"value": 10}]
    report = validator.validate(rows)
    assert report.warning_count >= 1
