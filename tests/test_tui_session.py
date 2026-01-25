import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tui.state import session


def test_session_persistence(tmp_path, monkeypatch):
    state_path = tmp_path / "tui_state.json"
    monkeypatch.setattr(session, "STATE_PATH", state_path)
    state = session.load_session_state()
    state.active_profile = "whale_watcher"
    profile_state = session.get_profile_state(state, "whale_watcher")
    profile_state.panel_order = ["whales", "alerts"]
    session.save_session_state(state)

    loaded = session.load_session_state()
    assert loaded.active_profile == "whale_watcher"
    loaded_profile_state = session.get_profile_state(loaded, "whale_watcher")
    assert loaded_profile_state.panel_order == ["whales", "alerts"]
