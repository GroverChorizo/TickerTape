from tui.themes.palettes import DEFAULT_THEME_ID
from tui.themes.theme_manager import ThemeManager
from tui.state import session as session_state


def test_theme_manager_default(tmp_path, monkeypatch):
    monkeypatch.setattr(session_state, "STATE_PATH", tmp_path / "state.json")
    manager = ThemeManager()
    manager.set_active_profile("day_trader")
    assert manager.current_id() == DEFAULT_THEME_ID


def test_theme_manager_persists_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(session_state, "STATE_PATH", tmp_path / "state.json")
    manager = ThemeManager()
    manager.set_active_profile("day_trader")
    manager.apply(app=DummyApp(), theme_name="dark_pro")
    reloaded = ThemeManager()
    reloaded.set_active_profile("day_trader")
    assert reloaded.current_id() == "dark_pro"


class DummyApp:
    def apply_palette(self, palette) -> None:
        self.palette = palette


def test_theme_manager_lists_all_themes(tmp_path, monkeypatch):
    monkeypatch.setattr(session_state, "STATE_PATH", tmp_path / "state.json")
    manager = ThemeManager()
    available = manager.available()
    assert set(available) == {"cypherpunk", "dark_pro", "matrix", "minimal"}
