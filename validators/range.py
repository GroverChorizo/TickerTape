"""Range validator."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

from .base import Validator
from .report import ValidationReport


class RangeValidator(Validator):
    """Validate numeric ranges for fields."""

    name = "range"

    def __init__(self, field_ranges: Dict[str, Tuple[float, float]]) -> None:
        self.field_ranges = dict(field_ranges)

    def validate(self, data: Iterable[Any]) -> ValidationReport:
        report = ValidationReport(validator=self.name)
        for idx, row in enumerate(data):
            if not isinstance(row, dict):
                report.errors.append(f"row {idx} is not a dict")
                continue
            for field, (min_val, max_val) in self.field_ranges.items():
                value = row.get(field)
                if value is None:
                    continue
                try:
                    num = float(value)
                except (TypeError, ValueError):
                    report.errors.append(f"row {idx} field {field} not numeric")
                    continue
                if num < min_val or num > max_val:
                    report.errors.append(f"row {idx} field {field} out of range {num}")
        return report
