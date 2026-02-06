"""Validator package scaffolding."""

from pathlib import Path
import sys

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from .base import Validator
from .duplicate import DuplicateValidator
from .missingness import MissingnessValidator
from .monotonic import MonotonicValidator
from .outlier import OutlierValidator
from .range import RangeValidator
from .report import ValidationReport
from .registry import (
    clear_registry,
    register_validator,
    registered_validators,
    run_validators,
)
from .schema import SchemaValidator

__all__ = [
    "Validator",
    "ValidationReport",
    "SchemaValidator",
    "MissingnessValidator",
    "RangeValidator",
    "MonotonicValidator",
    "DuplicateValidator",
    "OutlierValidator",
    "clear_registry",
    "register_validator",
    "registered_validators",
    "run_validators",
]
