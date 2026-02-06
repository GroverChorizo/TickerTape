"""Schema validator."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Tuple

from .base import Validator
from .report import ValidationReport


TypeSpec = type | Tuple[type, ...]


class SchemaValidator(Validator):
    """Validate required/optional fields and basic types."""

    name = "schema"

    def __init__(
        self,
        required: Mapping[str, TypeSpec],
        optional: Mapping[str, TypeSpec] | None = None,
    ) -> None:
        self.required = dict(required)
        self.optional = dict(optional or {})

    def validate(self, data: Iterable[Any]) -> ValidationReport:
        report = ValidationReport(validator=self.name)
        rows = list(data)
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                report.errors.append(f"row {idx} is not a dict")
                continue
            for field, expected in self.required.items():
                if field not in row or row.get(field) is None:
                    report.errors.append(f"row {idx} missing {field}")
                    continue
                value = row.get(field)
                if not isinstance(value, expected):
                    report.errors.append(
                        f"row {idx} field {field} type {type(value).__name__}"
                    )
            for field, expected in self.optional.items():
                if field not in row or row.get(field) is None:
                    continue
                value = row.get(field)
                if not isinstance(value, expected):
                    report.warnings.append(
                        f"row {idx} optional {field} type {type(value).__name__}"
                    )
        report.metadata["rows"] = len(rows)
        return report
