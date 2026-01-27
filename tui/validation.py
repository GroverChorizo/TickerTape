"""Validation helpers for dataset snapshots."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from validators import (
    DuplicateValidator,
    MissingnessValidator,
    MonotonicValidator,
    OutlierValidator,
    RangeValidator,
    SchemaValidator,
)
from validators.report import ValidationReport


_LIST_KEYS = ("rows", "events", "trades", "data", "items", "funding")


def extract_rows(snapshot: Any) -> List[Dict[str, Any]]:
    if snapshot is None:
        return []
    if isinstance(snapshot, list):
        return [row for row in snapshot if isinstance(row, dict)]
    if isinstance(snapshot, dict):
        for key in _LIST_KEYS:
            value = snapshot.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
        return [snapshot]
    return []


def run_validation(rows: List[Dict[str, Any]]) -> List[ValidationReport]:
    validators = build_default_validators(rows)
    reports: List[ValidationReport] = []
    for validator in validators:
        reports.append(validator.validate(rows))
    return reports


def summarize_reports(reports: Iterable[ValidationReport]) -> Dict[str, Any]:
    total_errors = 0
    total_warnings = 0
    by_validator: Dict[str, Dict[str, int]] = {}
    for report in reports:
        total_errors += report.error_count
        total_warnings += report.warning_count
        by_validator[report.validator] = {
            "errors": report.error_count,
            "warnings": report.warning_count,
        }
    return {
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "by_validator": by_validator,
    }


def build_default_validators(rows: List[Dict[str, Any]]):
    if not rows:
        return []
    sample = rows[0]
    required: Dict[str, type | tuple[type, ...]] = {}
    for key, value in sample.items():
        if value is None:
            continue
        required[key] = _type_spec(value)

    validators = [SchemaValidator(required=required)]

    missing_fields = list(required.keys())
    if missing_fields:
        validators.append(MissingnessValidator(missing_fields, max_missing_ratio=0.1))

    range_fields: Dict[str, tuple[float, float]] = {}
    for key in required.keys():
        norm = key.lower()
        if "funding" in norm and "rate" in norm:
            range_fields[key] = (-0.04, 0.04)
        elif norm in {"rate", "funding_rate"}:
            range_fields[key] = (-0.04, 0.04)
        elif "notional" in norm or "size" in norm or "amount" in norm:
            range_fields[key] = (0.0, float("inf"))
    if range_fields:
        validators.append(RangeValidator(range_fields))

    ts_field = _first_present(required.keys(), ["timestamp_ms", "timestamp", "time"])
    if ts_field:
        validators.append(MonotonicValidator(ts_field, strict=True))

    if ts_field and "id" in required:
        validators.append(DuplicateValidator([ts_field, "id"]))

    outlier_field = _first_present(
        required.keys(), ["notional_usd", "notional", "size", "price"]
    )
    if outlier_field:
        validators.append(OutlierValidator(outlier_field, z_threshold=4.0))

    return validators


def _first_present(keys: Iterable[str], candidates: Iterable[str]) -> Optional[str]:
    key_set = {str(k) for k in keys}
    for candidate in candidates:
        if candidate in key_set:
            return candidate
    return None


def _type_spec(value: Any) -> type | tuple[type, ...]:
    if isinstance(value, bool):
        return bool
    if isinstance(value, int):
        return (int, float)
    if isinstance(value, float):
        return (int, float)
    return type(value)
