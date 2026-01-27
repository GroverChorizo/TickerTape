import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.app import TickerTapeApp
from tui.config import TuiConfig, save_config


def _make_app(tmp_path):
    config = TuiConfig(
        mode="offline_demo",
        data_root=tmp_path / "data",
        profile="day_trader",
        secrets_path=None,
        alerts={},
        panel_overrides={},
        config_path=tmp_path / "config.json",
    )
    save_config(config)
    return TickerTapeApp(config)


def test_config_and_sidebar_commands(tmp_path):
    app = _make_app(tmp_path)
    message = app._cmd_config("config", [])
    assert "profile=day_trader" in message

    assert app.sidebar_hidden is False
    message = app._cmd_sidebar("sidebar", [])
    assert "hidden" in message
    assert app.sidebar_hidden is True


def test_export_and_log_export(tmp_path):
    app = _make_app(tmp_path)
    export_message = app._cmd_export("export", ["screen", "txt"])
    assert "Exported to" in export_message
    path = export_message.split("Exported to")[-1].strip()
    assert Path(path).exists()

    log_message = app._cmd_log_export("log_export", [])
    assert "Logs exported to" in log_message
    log_path = log_message.split("Logs exported to")[-1].strip()
    payload = json.loads(Path(log_path).read_text(encoding="utf-8"))
    assert "history" in payload


def test_reload_and_quit(tmp_path):
    app = _make_app(tmp_path)
    app.config.profile = "day_trader"
    save_config(app.config)
    message = app._cmd_reload("reload", [])
    assert "Config reloaded" in message

    called = {"exit": False}

    def _exit():
        called["exit"] = True

    app.exit = _exit  # type: ignore[assignment]
    quit_message = app._cmd_quit("quit", [])
    assert called["exit"] is True
    assert "Exiting" in quit_message
