from tui.themes import theme_manager
from tui.themes.palettes import DEFAULT_THEME_ID


def test_theme_manager_default(tmp_path, monkeypatch):
    monkeypatch.setattr(theme_manager, "THEME_STATE_PATH", tmp_path / "themes.json")
    assert theme_manager.get_theme_for_profile("day_trader") == DEFAULT_THEME_ID


def test_theme_manager_persists_selection(tmp_path, monkeypatch):
    path = tmp_path / "themes.json"
    monkeypatch.setattr(theme_manager, "THEME_STATE_PATH", path)
    theme_id = theme_manager.set_theme_for_profile("day_trader", "dark_pro")
    assert theme_id == "dark_pro"
    assert theme_manager.get_theme_for_profile("day_trader") == "dark_pro"
