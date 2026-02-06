import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.config import TuiConfig, load_config
from tui.state.session import SessionState, get_profile_state
from tui.ui.screens.settings import SettingsPayload, apply_settings


def test_apply_settings_updates_config_and_session(tmp_path):
    config_path = tmp_path / "config.json"
    data_root = tmp_path / "data" / "parquet"
    config = TuiConfig(
        mode="offline_demo",
        data_root=data_root,
        profile="day_trader",
        secrets_path=None,
        alerts={},
        panel_overrides={},
        config_path=config_path,
    )
    session_state = SessionState(active_profile="day_trader", profiles={})
    applied = {}

    def apply_theme(profile: str, theme: str) -> None:
        applied["profile"] = profile
        applied["theme"] = theme

    payload = SettingsPayload(
        profile="liquidation_hunter",
        theme="matrix",
        panels=["liquidations"],
        alerts={"whale_trades": True},
    )
    apply_settings(config, session_state, payload, apply_theme=apply_theme)

    loaded = load_config({"config_path": str(config_path)})
    assert loaded.profile == "liquidation_hunter"
    assert loaded.alerts.get("whale_trades") is True
    assert loaded.panel_overrides.get("liquidation_hunter") == ["liquidations"]
    assert session_state.active_profile == "liquidation_hunter"
    profile_state = get_profile_state(session_state, "liquidation_hunter")
    assert profile_state.panel_order == ["liquidations"]
    assert applied == {"profile": "liquidation_hunter", "theme": "matrix"}
