import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.state import session as session_state
from tui.state.session import load_session_state
from tui.ui.fullscreen import toggle_fullscreen
from tui.ui.density import apply_density_state, toggle_density


class DummyScreen:
    def __init__(self) -> None:
        self.classes = set()

    def add_class(self, name: str) -> None:
        self.classes.add(name)

    def remove_class(self, name: str) -> None:
        self.classes.discard(name)


class DummyApp:
    def __init__(self, state):
        self.session_state = state


def test_fullscreen_toggle_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(session_state, "STATE_PATH", tmp_path / "state.json")
    state = load_session_state()
    app = DummyApp(state)
    screen = DummyScreen()

    assert toggle_fullscreen(app, screen, "day_trader") is True
    assert "fullscreen" in screen.classes

    reloaded = load_session_state()
    assert reloaded.profiles["day_trader"].fullscreen is True

    assert toggle_fullscreen(app, screen, "day_trader") is False
    assert "fullscreen" not in screen.classes


def test_density_toggle_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(session_state, "STATE_PATH", tmp_path / "state.json")
    state = load_session_state()
    app = DummyApp(state)
    screen = DummyScreen()

    density = toggle_density(app, screen, "day_trader")
    assert density == "compact"
    assert "density-compact" in screen.classes

    apply_density_state(app, screen, "day_trader")
    assert "density-compact" in screen.classes

    density = toggle_density(app, screen, "day_trader")
    assert density == "comfortable"
    assert "density-comfortable" in screen.classes
