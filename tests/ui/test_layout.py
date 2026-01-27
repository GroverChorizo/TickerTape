import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.ui.layout import apply_layout, layout_class


class DummyScreen:
    def __init__(self) -> None:
        self.classes = set()

    def add_class(self, name: str) -> None:
        self.classes.add(name)

    def remove_class(self, name: str) -> None:
        self.classes.discard(name)


def test_layout_class_breakpoints():
    assert layout_class(200) == "layout-ultra"
    assert layout_class(130) == "layout-wide"
    assert layout_class(105) == "layout-standard"
    assert layout_class(90) == "layout-narrow"
    assert layout_class(60) == "layout-compact"


def test_apply_layout_sets_class():
    screen = DummyScreen()
    apply_layout(screen, 120)
    assert "layout-wide" in screen.classes
    apply_layout(screen, 70)
    assert "layout-wide" not in screen.classes
    assert "layout-compact" in screen.classes
