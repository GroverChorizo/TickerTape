"""Base validator interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable


class Validator(ABC):
    """Abstract data validator."""

    name: str

    @abstractmethod
    def validate(self, data: Iterable[Any]) -> Any:
        raise NotImplementedError
