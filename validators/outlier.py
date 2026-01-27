"""Outlier validator."""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any, Iterable, List

from .base import Validator
from .report import ValidationReport


class OutlierValidator(Validator):
    """Flag outliers using Z-score."""

    name = "outlier"

    def __init__(self, field: str, z_threshold: float = 4.0) -> None:
        self.field = field
        self.z_threshold = z_threshold

    def validate(self, data: Iterable[Any]) -> ValidationReport:
        report = ValidationReport(validator=self.name)
        values: List[float] = []
        rows: List[Any] = list(data)
        for row in rows:
            if not isinstance(row, dict):
                continue
            value = row.get(self.field)
            if value is None:
                continue
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue
        if len(values) < 2:
            report.warnings.append("insufficient data for outlier detection")
            return report
        sigma = pstdev(values)
        mu = mean(values)
        report.metadata.update(
            {
                "mean": mu,
                "stdev": sigma,
                "count": len(values),
                "threshold": self.z_threshold,
            }
        )
        if sigma == 0:
            report.warnings.append("zero variance in data")
            return report
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            value = row.get(self.field)
            if value is None:
                continue
            try:
                num = float(value)
            except (TypeError, ValueError):
                continue
            z = abs((num - mu) / sigma)
            if z > self.z_threshold:
                report.warnings.append(f"row {idx} field {self.field} z={z:.2f}")
        return report
