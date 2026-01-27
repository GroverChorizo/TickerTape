from pathlib import Path


def test_theme_css_defines_tokens():
    css = Path("tui/tui.css").read_text(encoding="utf-8")
    for theme_id in ["cypherpunk", "dark_pro", "matrix", "minimal"]:
        assert f"Screen.theme-{theme_id}" in css
    for token in [
        "--tt-bg-primary",
        "--tt-bg-panel",
        "--tt-text-primary",
        "--tt-text-muted",
        "--tt-border-panel",
        "--tt-border-focus",
        "--tt-accent-cyan",
        "--tt-accent-purple",
        "--tt-accent-green",
        "--tt-accent-orange",
        "--tt-accent-red",
        "--tt-space-1",
        "--tt-space-2",
        "--tt-space-3",
        "--tt-space-4",
        "--tt-space-5",
        "--tt-pad-x",
        "--tt-pad-y",
    ]:
        assert token in css
