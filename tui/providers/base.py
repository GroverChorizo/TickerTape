"""Provider interface and error wrappers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderError(Exception):
    message: str
    status: Optional[int] = None
    url: Optional[str] = None

    def __str__(self) -> str:
        if self.status and self.url:
            return f"HTTP {self.status} {self.url}: {self.message}"
        return self.message
