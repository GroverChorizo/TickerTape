import pytest


def test_tui_import_smoke():
    pytest.importorskip("httpx")
    __import__("tui.app")
