"""Registry for validators."""

from __future__ import annotations

from typing import Iterable, List, Optional

from .base import Validator
from .report import ValidationReport


_REGISTRY: List[Validator] = []


def register_validator(validator: Validator) -> None:
    """Register a validator instance by name (no duplicates)."""
    for existing in _REGISTRY:
        if existing.name == validator.name:
            return
    _REGISTRY.append(validator)


def registered_validators() -> List[Validator]:
    return list(_REGISTRY)


def clear_registry() -> None:
    _REGISTRY.clear()


def run_validators(
    data: Iterable[object], validators: Optional[Iterable[Validator]] = None
) -> List[ValidationReport]:
    reports: List[ValidationReport] = []
    for validator in validators or _REGISTRY:
        report = validator.validate(data)
        reports.append(report)
    return reports
