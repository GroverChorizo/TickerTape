"""Base panel interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Panel(ABC):
    """Abstract panel that can render content for a profile screen."""

    panel_id: str
    title: str

    @abstractmethod
    def render(self) -> object:
        raise NotImplementedError
