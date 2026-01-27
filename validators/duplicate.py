"""Duplicate validator."""

from __future__ import annotations

from typing import Any, Iterable, List, Tuple

from .base import Validator
from .report import ValidationReport


class DuplicateValidator(Validator):
    """Detect duplicate records based on key fields."""

    name = "duplicate"

    def __init__(self, key_fields: Iterable[str]) -> None:
        self.key_fields = list(key_fields)

    def validate(self, data: Iterable[Any]) -> ValidationReport:
        report = ValidationReport(validator=self.name)
        seen: set[Tuple[Any, ...]] = set()
        for idx, row in enumerate(data):
            if not isinstance(row, dict):
                report.errors.append(f"row {idx} is not a dict")
                continue
            key: List[Any] = []
            missing = False
            for field in self.key_fields:
                if field not in row:
                    missing = True
                    break
                key.append(row.get(field))
            if missing:
                report.warnings.append(f"row {idx} missing key fields")
                continue
            key_tuple = tuple(key)
            if key_tuple in seen:
                report.errors.append(f"row {idx} duplicate key {key_tuple}")
            else:
                seen.add(key_tuple)
        report.metadata["unique_keys"] = len(seen)
        return report
