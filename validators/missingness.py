"""Missingness validator."""

from __future__ import annotations

from typing import Any, Iterable

from .base import Validator
from .report import ValidationReport


class MissingnessValidator(Validator):
    """Validate missing field ratios."""

    name = "missingness"

    def __init__(self, fields: Iterable[str], max_missing_ratio: float = 0.0) -> None:
        self.fields = list(fields)
        self.max_missing_ratio = max_missing_ratio

    def validate(self, data: Iterable[Any]) -> ValidationReport:
        report = ValidationReport(validator=self.name)
        rows = list(data)
        total = len(rows)
        if total == 0:
            report.warnings.append("no rows")
            return report
        missing_counts = {field: 0 for field in self.fields}
        for row in rows:
            if not isinstance(row, dict):
                for field in self.fields:
                    missing_counts[field] += 1
                continue
            for field in self.fields:
                value = row.get(field)
                if value is None or value == "":
                    missing_counts[field] += 1
        for field, count in missing_counts.items():
            ratio = count / total
            report.metadata[f"{field}_missing_ratio"] = ratio
            if ratio > self.max_missing_ratio:
                report.errors.append(
                    f"field {field} missing ratio {ratio:.2f} > {self.max_missing_ratio:.2f}"
                )
        return report
