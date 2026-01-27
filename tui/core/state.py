"""In-memory state store for profile snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time


@dataclass
class SnapshotState:
    data: Optional[Any] = None
    last_update_ms: Optional[int] = None
    last_error: Optional[str] = None
    backoff_s: float = 0.0


@dataclass
class ProfileState:
    snapshots: Dict[str, SnapshotState] = field(default_factory=dict)

    def get_snapshot(self, key: str) -> SnapshotState:
        if key not in self.snapshots:
            self.snapshots[key] = SnapshotState()
        return self.snapshots[key]


class StateStore:
    def __init__(self) -> None:
        self._profiles: Dict[str, ProfileState] = {}

    def profile(self, name: str) -> ProfileState:
        if name not in self._profiles:
            self._profiles[name] = ProfileState()
        return self._profiles[name]

    def update_snapshot(
        self, profile: str, key: str, data: Any, *, ts_ms: Optional[int] = None
    ) -> None:
        snap = self.profile(profile).get_snapshot(key)
        snap.data = data
        snap.last_update_ms = ts_ms or int(time.time() * 1000)
        snap.last_error = None
        snap.backoff_s = 0.0

    def set_error(
        self, profile: str, key: str, error: str, *, backoff_s: float = 0.0
    ) -> None:
        snap = self.profile(profile).get_snapshot(key)
        snap.last_error = error
        snap.backoff_s = backoff_s
