from pathlib import Path


def test_theme_css_defines_tokens():
    css = Path("tui/tui.css").read_text(encoding="utf-8")
    for selector in [
        "Screen.layout-ultra",
        "Screen.layout-wide",
        "Screen.layout-narrow",
        "Screen.layout-compact",
        "Screen.density-compact",
        "Screen.density-comfortable",
        "Screen.fullscreen",
        "TabCarousel",
        "StatusBar",
    ]:
        assert selector in css
