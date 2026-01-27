import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from validators.duplicate import DuplicateValidator


def test_duplicate_validator_detects_dupes():
    validator = DuplicateValidator(["ts", "id"])
    rows = [{"ts": 1, "id": "a"}, {"ts": 1, "id": "a"}]
    report = validator.validate(rows)
    assert report.error_count == 1
