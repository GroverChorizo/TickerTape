import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.state import session as session_state
from tui.state.session import load_session_state, get_profile_state
from tui.ui.custom_dashboard import (
    PanelSize,
    apply_custom_dashboard,
    create_dashboard_from_state,
    load_custom_dashboards,
    save_custom_dashboard,
)


def test_custom_dashboard_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(session_state, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(
        "tui.ui.custom_dashboard.DEFAULT_DASHBOARD_PATH", tmp_path / "dash.json"
    )
    state = load_session_state()
    profile = get_profile_state(state, "day_trader")
    profile.panel_order = ["liquidations", "funding"]
    profile.panel_sizes = {"liquidations": {"width": 40, "height": 10}}

    layout = create_dashboard_from_state(state, "day_trader", name="custom")
    save_custom_dashboard(layout, path=Path(tmp_path / "dash.json"))

    dashboards = load_custom_dashboards(path=Path(tmp_path / "dash.json"))
    assert "custom" in dashboards
    loaded = dashboards["custom"]
    assert loaded.panels == ["liquidations", "funding"]
    assert loaded.panel_sizes["liquidations"].width == 40


def test_apply_custom_dashboard_updates_state(tmp_path, monkeypatch):
    monkeypatch.setattr(session_state, "STATE_PATH", tmp_path / "state.json")
    state = load_session_state()
    layout = create_dashboard_from_state(state, "day_trader", name="custom")
    layout = layout.__class__(
        name=layout.name,
        panels=["whales"],
        panel_sizes={"whales": PanelSize(width=32, height=8)},
        created_ts=layout.created_ts,
    )
    apply_custom_dashboard(state, "day_trader", layout)
    updated = get_profile_state(state, "day_trader")
    assert updated.panel_order == ["whales"]
