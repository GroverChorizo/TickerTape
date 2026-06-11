"""Bot harness: strategy determinism, contract writers, kill-switch.

Strategy tests run on REAL bars from the repo's datadogs store (skipped when
absent) — no fabricated OHLCV, per hard rule #1. Contract-writer tests use
bot-output JSON only.
"""
from __future__ import annotations

import json

import pytest

from bots.runner import Bot, append_signal, read_state, write_state_atomic
from bots.strategies import StrategyError, ma20_60_long_short, vsma_band


def _real_btc_15m():
    from datadogs.config import data_dir

    if not (data_dir() / "BTC-15m.csv").exists():
        pytest.skip("no real BTC-15m.csv — run: python -m datadogs fetch BTC 15m")
    from data_loader.loader import load

    return load("BTC", "15m", quiet=True)


# ── strategy ──────────────────────────────────────────────────────────────


def test_ma20_60_deterministic_on_real_bars():
    df = _real_btc_15m()
    a = ma20_60_long_short(df)
    b = ma20_60_long_short(df)
    assert a == b
    assert a.position in (-1, 0, 1)
    assert a.bar_ts_ms == int(df.index[-1].value // 1_000_000)
    assert set(a.meta) == {"ma20", "ma60"}


def test_ma20_60_position_matches_ma_relation():
    df = _real_btc_15m()
    v = ma20_60_long_short(df)
    if v.meta["ma20"] > v.meta["ma60"]:
        assert v.position == 1
    elif v.meta["ma20"] < v.meta["ma60"]:
        assert v.position == -1


def test_ma20_60_rejects_insufficient_warmup():
    df = _real_btc_15m()
    with pytest.raises(StrategyError):
        ma20_60_long_short(df.iloc[:30])  # real bars, too few of them


def _real_btc_4h():
    from datadogs.config import data_dir

    if not (data_dir() / "BTC-4h.csv").exists():
        pytest.skip("no real BTC-4h.csv — run: python -m datadogs backfill BTC 4h --days 900")
    from data_loader.loader import load

    return load("BTC", "4h", quiet=True)


def test_vsma_band_deterministic_on_real_bars():
    df = _real_btc_4h()
    a = vsma_band(df)
    b = vsma_band(df)
    assert a == b
    assert a.position in (-1, 0, 1)
    assert a.bar_ts_ms == int(df.index[-1].value // 1_000_000)
    assert {"vsma", "atr", "trend"} <= set(a.meta)
    assert a.meta["trend"] in (-1, 0, 1)
    assert a.meta["atr"] > 0


def test_vsma_band_rejects_insufficient_warmup():
    df = _real_btc_4h()
    with pytest.raises(StrategyError):
        vsma_band(df.iloc[:50])  # real bars, below the 60-bar warmup


def test_vsma_band_position_consistent_with_trend_exit_rule():
    # The replay exits when trend flips against the position, so a held
    # position can never coexist with a fully opposite trend on the last bar.
    df = _real_btc_4h()
    v = vsma_band(df)
    if v.position == 1:
        assert v.meta["trend"] != -1
    elif v.position == -1:
        assert v.meta["trend"] != 1


# ── contract writers ──────────────────────────────────────────────────────


def test_signal_append_and_state_roundtrip(tmp_path, monkeypatch):
    import bots.runner as runner

    monkeypatch.setattr(runner, "SIGNALS_DIR", tmp_path / "signals")
    monkeypatch.setattr(runner, "STATE_DIR", tmp_path / "state")
    # the repo's tmp_path fixture reuses a stable dir per test — start clean
    tape = tmp_path / "signals" / "signals.jsonl"
    if tape.exists():
        tape.unlink()

    append_signal({"event": "no_trade_heartbeat", "strategy": "ma20_60",
                   "mode": "shadow"})
    append_signal({"event": "entry_signal", "strategy": "ma20_60",
                   "side": "long", "mode": "shadow"})
    lines = (tmp_path / "signals" / "signals.jsonl").read_text().splitlines()
    assert len(lines) == 2  # append-only, one object per line
    assert json.loads(lines[1])["event"] == "entry_signal"

    st = {"bot_id": "ma20_60_BTC_15m", "mode": "shadow", "alive_at": 1,
          "last_bar_processed": None, "open_position": None, "errors_24h": 0}
    write_state_atomic("ma20_60_BTC_15m", st)
    assert read_state("ma20_60_BTC_15m") == st
    leftovers = list((tmp_path / "state").glob("*.tmp"))
    assert leftovers == []  # atomic write leaves no temp files


def test_kill_switch_exits_clean(tmp_path, monkeypatch):
    import bots.runner as runner

    monkeypatch.setattr(runner, "SIGNALS_DIR", tmp_path / "signals")
    monkeypatch.setattr(runner, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(runner, "KILL_PATH", tmp_path / "state" / "KILL")
    (tmp_path / "state").mkdir(exist_ok=True)
    (tmp_path / "state" / "KILL").touch()

    bot = Bot("ma20_60", "BTC", "15m", mode="shadow")
    assert bot.run(once=False) == 0  # exits on KILL, not on --once


def test_shadow_mode_is_the_only_mode():
    with pytest.raises(SystemExit):
        Bot("ma20_60", "BTC", "15m", mode="live")
