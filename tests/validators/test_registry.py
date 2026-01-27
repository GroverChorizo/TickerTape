import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from validators.base import Validator
from validators.registry import (
    clear_registry,
    register_validator,
    registered_validators,
    run_validators,
)
from validators.report import ValidationReport


class DummyValidator(Validator):
    name = "dummy"

    def validate(self, data):
        errors = ["empty"] if not list(data) else []
        return ValidationReport(validator=self.name, errors=errors)


def test_register_and_run_validators():
    clear_registry()
    validator = DummyValidator()
    register_validator(validator)
    register_validator(validator)
    assert len(registered_validators()) == 1

    reports = run_validators([])
    assert reports
    report = reports[0]
    assert report.validator == "dummy"
    assert report.error_count == 1
    assert report.ok is False

    reports = run_validators([1])
    assert reports[0].error_count == 0
