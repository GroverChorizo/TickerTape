"""Custom dashboard persistence and application helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import json
import time

from tui.state.session import SessionState, get_profile_state, save_session_state


DEFAULT_DASHBOARD_PATH = Path("data/custom_dashboards.json")


@dataclass(frozen=True)
class PanelSize:
    width: int | None = None
    height: int | None = None

    def to_dict(self) -> Dict[str, int]:
        payload: Dict[str, int] = {}
        if self.width is not None:
            payload["width"] = self.width
        if self.height is not None:
            payload["height"] = self.height
        return payload

    @classmethod
    def from_dict(cls, payload: Dict) -> "PanelSize":
        width = payload.get("width")
        height = payload.get("height")
        return cls(
            width=int(width) if width is not None else None,
            height=int(height) if height is not None else None,
        )


@dataclass(frozen=True)
class DashboardLayout:
    name: str
    panels: List[str]
    panel_sizes: Dict[str, PanelSize]
    created_ts: float

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "panels": list(self.panels),
            "panel_sizes": {k: v.to_dict() for k, v in self.panel_sizes.items()},
            "created_ts": self.created_ts,
        }

    @classmethod
    def from_dict(cls, payload: Dict) -> "DashboardLayout":
        sizes = payload.get("panel_sizes", {}) or {}
        panel_sizes = {k: PanelSize.from_dict(v) for k, v in sizes.items()}
        return cls(
            name=str(payload.get("name", "")),
            panels=[str(p) for p in payload.get("panels", [])],
            panel_sizes=panel_sizes,
            created_ts=float(payload.get("created_ts", 0.0)),
        )


def load_custom_dashboards(
    path: Path = DEFAULT_DASHBOARD_PATH,
) -> Dict[str, DashboardLayout]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    dashboards: Dict[str, DashboardLayout] = {}
    for name, item in payload.get("dashboards", {}).items():
        dashboards[name] = DashboardLayout.from_dict(item)
    return dashboards


def save_custom_dashboard(
    layout: DashboardLayout, path: Path = DEFAULT_DASHBOARD_PATH
) -> None:
    dashboards = load_custom_dashboards(path)
    dashboards[layout.name] = layout
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"dashboards": {k: v.to_dict() for k, v in dashboards.items()}}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def create_dashboard_from_state(
    state: SessionState, profile: str, name: Optional[str] = None
) -> DashboardLayout:
    profile_state = get_profile_state(state, profile)
    sizes = {
        panel: PanelSize.from_dict(size)
        for panel, size in (profile_state.panel_sizes or {}).items()
    }
    return DashboardLayout(
        name=name or profile,
        panels=list(profile_state.panel_order),
        panel_sizes=sizes,
        created_ts=time.time(),
    )


def apply_custom_dashboard(
    state: SessionState, profile: str, layout: DashboardLayout
) -> None:
    profile_state = get_profile_state(state, profile)
    if layout.panels:
        profile_state.panel_order = list(layout.panels)
    profile_state.panel_sizes = {
        panel: size.to_dict() for panel, size in layout.panel_sizes.items()
    }
    save_session_state(state)
