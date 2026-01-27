import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.widgets.panel_base import ResizablePanel


def test_resizable_panel_resize_methods():
    panel = ResizablePanel(panel_id="test", title="Test", min_width=10, min_height=4)
    width, height = panel.resize_to(30, 12)
    assert width == 30
    assert height == 12

    width, height = panel.resize_by(-50, -50)
    assert width == 10
    assert height == 4
