"""Base profile interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Profile(ABC):
    """Abstract profile definition for profile screens."""

    name: str
    label: str
    description: str

    @abstractmethod
    def build_screen(self) -> object:
        """Return a screen instance for this profile."""
        raise NotImplementedError
