"""Ops widgets: signal tape, bot health, and data health scan.

Fixtures here are bot-output JSON (signals/heartbeats) per the
Bot-TickerTape Interface Contract — never market data. The data-health
scan is tested against an empty store and, when present, the repo's real
datadogs store; no OHLCV rows are ever fabricated.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from tui.widgets.bot_health_panel import (_alive_style, _lag_style,
                                          read_bot_states)
from tui.widgets.data_health_panel import scan_health
from tui.widgets.signal_tape_panel import read_tail


# ── signal tape ───────────────────────────────────────────────────────────


def test_read_tail_missing_file_returns_empty(tmp_path):
    assert read_tail(tmp_path / "signals.jsonl") == []


def test_read_tail_parses_events_and_keeps_order(tmp_path):
    p = tmp_path / "signals.jsonl"
    events = [
        {"ts": 1781136900000, "strategy": "scalper_conservative",
         "event": "no_trade_heartbeat", "mode": "shadow"},
        {"ts": 1781137800000, "strategy": "scalper_conservative",
         "event": "entry_signal", "side": "long", "mode": "shadow",
         "confidence": 0.62},
    ]
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    out = read_tail(p)
    assert [e["event"] for e in out] == ["no_trade_heartbeat", "entry_signal"]


def test_read_tail_surfaces_malformed_lines_as_errors(tmp_path):
    p = tmp_path / "signals.jsonl"
    p.write_text('{"event": "no_trade_heartbeat"}\nnot json at all\n', encoding="utf-8")
    out = read_tail(p)
    assert len(out) == 2
    assert out[1]["event"] == "error"
    assert out[1]["strategy"] == "<malformed line>"


def test_read_tail_respects_tail_limit(tmp_path):
    p = tmp_path / "signals.jsonl"
    lines = [json.dumps({"event": "no_trade_heartbeat", "seq": i}) for i in range(10)]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = read_tail(p, n=3)
    assert [e["seq"] for e in out] == [7, 8, 9]


# ── bot health ────────────────────────────────────────────────────────────


def test_read_bot_states_missing_dir(tmp_path):
    assert read_bot_states(tmp_path / "state") == []


def test_read_bot_states_parses_heartbeat(tmp_path):
    d = tmp_path / "state"
    d.mkdir(exist_ok=True)
    hb = {"bot_id": "scalper_conservative", "mode": "shadow",
          "alive_at": 1781136910000, "last_bar_processed": 1781136900000,
          "data_lag_bars": 0, "open_position": None, "errors_24h": 0}
    (d / "scalper_conservative.json").write_text(json.dumps(hb), encoding="utf-8")
    out = read_bot_states(d)
    assert out == [hb]


def test_read_bot_states_surfaces_corrupt_file(tmp_path):
    d = tmp_path / "state"
    d.mkdir(exist_ok=True)
    (d / "broken_bot.json").write_text("{truncated", encoding="utf-8")
    out = read_bot_states(d)
    assert out[0]["bot_id"] == "broken_bot"
    assert "_error" in out[0]


def test_lag_thresholds_match_interface_contract():
    # green < 2 bars, yellow < 5, red otherwise (vault contract)
    assert _lag_style(0) == "green"
    assert _lag_style(1.9) == "green"
    assert _lag_style(2) == "yellow"
    assert _lag_style(5) == "red"
    assert _lag_style(None) == "red"


def test_alive_thresholds():
    assert _alive_style(30) == "green"
    assert _alive_style(300) == "yellow"
    assert _alive_style(3000) == "red"


# ── data health scan ──────────────────────────────────────────────────────


def test_scan_health_empty_store(tmp_path, monkeypatch):
    monkeypatch.setenv("QB_DATA_DIR", str(tmp_path / "empty_store"))
    assert scan_health() == []


def test_scan_health_real_store_if_present(monkeypatch):
    """Against the repo's actual datadogs store; skipped when absent so the
    test never needs (and never gets) fabricated CSVs."""
    monkeypatch.delenv("QB_DATA_DIR", raising=False)
    from datadogs.config import data_dir

    if not any(data_dir().glob("*.csv")):
        pytest.skip("no real datadogs store in ./data — run: python -m datadogs fetch-all")
    rows = scan_health()
    assert rows, "store has CSVs but scan returned nothing"
    for r in rows:
        assert r.status in {"OK", "STALE", "ERROR"}
        assert r.rows >= 0


# ── screen smoke (headless Textual pilot) ─────────────────────────────────


def test_ops_screen_tabs_switch_without_exceptions():
    textual = pytest.importorskip("textual")  # noqa: F841
    from textual.app import App
    from textual.widgets import TabbedContent

    from tui.config import TuiConfig
    from tui.state.session import SessionState
    from tui.ui.screens.ops import OpsScreen

    class _Host(App):
        def __init__(self) -> None:
            super().__init__()
            self.session_state = SessionState(active_profile="day_trader", profiles={})
            self.selected_symbol = "BTC"
            self.config = TuiConfig(
                mode="offline_demo",
                data_root=Path("data/parquet"),
                profile="day_trader",
                config_path=Path("data/test_config.json"),
                secrets_path=None,
            )

        def on_mount(self) -> None:
            self.push_screen(OpsScreen())

        def get_open_screens(self):
            return [{"key": "ops", "label": "Ops"}]

        def is_alert_enabled(self, _alert_name: str) -> bool:
            return False

        def emit_alert(self, **_kwargs) -> None:
            return None

    app = _Host()

    async def _run() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            tabs = app.screen.query_one(TabbedContent)
            for tab_id in ("ops_tab_data", "ops_tab_signals", "ops_tab_bots"):
                tabs.active = tab_id
                await pilot.pause()

    asyncio.run(_run())
