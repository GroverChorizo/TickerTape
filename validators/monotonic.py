"""Monotonic validator."""

from __future__ import annotations

from typing import Any, Iterable

from .base import Validator
from .report import ValidationReport


class MonotonicValidator(Validator):
    """Validate that a field is monotonic increasing."""

    name = "monotonic"

    def __init__(self, field: str, strict: bool = True) -> None:
        self.field = field
        self.strict = strict

    def validate(self, data: Iterable[Any]) -> ValidationReport:
        report = ValidationReport(validator=self.name)
        last = None
        for idx, row in enumerate(data):
            if not isinstance(row, dict):
                report.errors.append(f"row {idx} is not a dict")
                continue
            value = row.get(self.field)
            if value is None:
                report.warnings.append(f"row {idx} missing {self.field}")
                continue
            try:
                num = float(value)
            except (TypeError, ValueError):
                report.errors.append(f"row {idx} field {self.field} not numeric")
                continue
            if last is not None:
                if self.strict and num <= last:
                    report.errors.append(
                        f"row {idx} field {self.field} not strictly increasing"
                    )
                elif not self.strict and num < last:
                    report.errors.append(
                        f"row {idx} field {self.field} not nondecreasing"
                    )
            last = num
        return report
