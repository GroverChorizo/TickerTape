"""Bot runner: drives one strategy in shadow mode over the local CSV store.

    python -m bots.runner --strategy ma20_60 --symbol BTC --tf 15m [--once]

Contract (vault: Bot-TickerTape Interface Contract):
  * signals/signals.jsonl   append-only, one JSON object per line
  * state/<bot_id>.json     atomic rewrite (tmp + os.replace) every cycle
  * state/KILL exists       -> finish current step, write final state, exit
  * ts on every signal = the closed bar's OPEN time (ms UTC) so replay
    diffing can tie each event to an exact bar.

Shadow mode only: no orders, no execution code. The bot reads real bars
(kept fresh by the datadogs scheduler) and says what it WOULD do. Data and
venue are never mixed: one bot, one symbol file, one venue (the primary).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from bots.strategies import STRATEGIES, PositionView

SIGNALS_DIR = Path("signals")
STATE_DIR = Path("state")
KILL_PATH = STATE_DIR / "KILL"
VERSION = "0.1"

TIMEFRAME_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000,
                "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}


def now_ms() -> int:
    return int(time.time() * 1000)


def append_signal(event: Dict[str, Any]) -> None:
    SIGNALS_DIR.mkdir(exist_ok=True)
    with open(SIGNALS_DIR / "signals.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(event, separators=(",", ":")) + "\n")


def write_state_atomic(bot_id: str, state: Dict[str, Any]) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    target = STATE_DIR / f"{bot_id}.json"
    fd, tmp = tempfile.mkstemp(prefix=bot_id + ".", suffix=".tmp", dir=STATE_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=1)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_state(bot_id: str) -> Dict[str, Any]:
    p = STATE_DIR / f"{bot_id}.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


class Bot:
    def __init__(self, strategy: str, symbol: str, tf: str, mode: str = "shadow") -> None:
        if mode != "shadow":
            raise SystemExit("read-only phase: shadow mode only, no execution code")
        self.strategy_name = strategy
        self.signal_fn = STRATEGIES[strategy]
        self.symbol = symbol.upper()
        self.tf = tf
        self.mode = mode
        self.bot_id = f"{strategy}_{self.symbol}_{tf}"
        prior = read_state(self.bot_id)
        self.last_bar_processed: Optional[int] = prior.get("last_bar_processed")
        self.open_position: Optional[Dict[str, Any]] = prior.get("open_position")
        self._error_ts: list[int] = prior.get("error_ts", [])

    # ── one cycle ─────────────────────────────────────────────────────────

    def cycle(self) -> bool:
        """Process at most one new closed bar. Returns True if one was processed."""
        view = self._compute()
        if view is None:
            self._heartbeat(data_lag_bars=None)
            return False

        lag = max(0.0, (now_ms() - view.bar_ts_ms) / TIMEFRAME_MS[self.tf] - 1)
        if self.last_bar_processed is not None and view.bar_ts_ms <= self.last_bar_processed:
            self._heartbeat(data_lag_bars=lag)      # no new closed bar yet
            return False

        first_run = self.last_bar_processed is None
        prev_side = (self.open_position or {}).get("side")
        new_side = {1: "long", -1: "short", 0: None}[view.position]

        if first_run:
            # Inheriting an in-progress MA state is not a fresh cross — record
            # the position without fabricating an entry event for an old bar.
            self._emit(view, "no_trade_heartbeat", new_side,
                       extra={"meta": {**view.meta, "initialized": True}})
        elif new_side != prev_side:
            if prev_side is not None:
                self._emit(view, "exit_signal", prev_side)
            if new_side is not None:
                self._emit(view, "entry_signal", new_side)
        else:
            self._emit(view, "no_trade_heartbeat", new_side)

        self.open_position = (
            {"side": new_side, "since_ts": view.bar_ts_ms, "ref_price": view.bar_close}
            if new_side else None
        )
        self.last_bar_processed = view.bar_ts_ms
        self._heartbeat(data_lag_bars=lag)
        return True

    def _compute(self) -> Optional[PositionView]:
        try:
            from data_loader.loader import load
            df = load(self.symbol, self.tf, quiet=True)
            return self.signal_fn(df)
        except Exception as exc:  # StrategyError, missing CSV, contract violation
            self._record_error(exc)
            return None

    # ── contract writers ──────────────────────────────────────────────────

    def _emit(self, view: PositionView, event: str, side: Optional[str],
              extra: Optional[Dict[str, Any]] = None) -> None:
        sig: Dict[str, Any] = {
            "ts": view.bar_ts_ms, "emitted_at": now_ms(),
            "strategy": self.strategy_name, "version": VERSION,
            "symbol": self.symbol, "tf": self.tf,
            "event": event, "side": side,
            "bar_close": view.bar_close, "mode": self.mode,
            "meta": view.meta,
        }
        if extra:
            sig.update(extra)
        append_signal(sig)
        print(f"[{self.bot_id}] {event} side={side} bar={view.bar_ts_ms} "
              f"close={view.bar_close}", flush=True)

    def _record_error(self, exc: Exception) -> None:
        self._error_ts.append(now_ms())
        append_signal({"ts": self.last_bar_processed, "emitted_at": now_ms(),
                       "strategy": self.strategy_name, "version": VERSION,
                       "symbol": self.symbol, "tf": self.tf, "event": "error",
                       "side": None, "mode": self.mode, "meta": {"error": str(exc)[:200]}})
        print(f"[{self.bot_id}] ERROR {exc}", file=sys.stderr, flush=True)

    def _heartbeat(self, data_lag_bars: Optional[float]) -> None:
        cutoff = now_ms() - 86_400_000
        self._error_ts = [t for t in self._error_ts if t > cutoff]
        write_state_atomic(self.bot_id, {
            "bot_id": self.bot_id, "mode": self.mode, "alive_at": now_ms(),
            "last_bar_processed": self.last_bar_processed,
            "data_lag_bars": round(data_lag_bars, 2) if data_lag_bars is not None else None,
            "open_position": self.open_position,
            "errors_24h": len(self._error_ts), "error_ts": self._error_ts,
        })

    # ── loop ──────────────────────────────────────────────────────────────

    def run(self, once: bool = False, poll_s: float = 60.0) -> int:
        print(f"[{self.bot_id}] starting mode={self.mode} "
              f"(kill-switch: {KILL_PATH})", flush=True)
        while True:
            if KILL_PATH.exists():
                self._heartbeat(data_lag_bars=None)
                print(f"[{self.bot_id}] KILL detected — exiting cleanly", flush=True)
                return 0
            self.cycle()
            if once:
                return 0
            time.sleep(poll_s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="bots.runner", description=__doc__)
    ap.add_argument("--strategy", required=True, choices=sorted(STRATEGIES))
    ap.add_argument("--symbol", default="BTC")
    ap.add_argument("--tf", default="15m", choices=sorted(TIMEFRAME_MS, key=TIMEFRAME_MS.get))
    ap.add_argument("--mode", default="shadow", choices=["shadow"])
    ap.add_argument("--once", action="store_true", help="one cycle then exit")
    ap.add_argument("--poll", type=float, default=60.0, help="seconds between cycles")
    a = ap.parse_args(argv)
    return Bot(a.strategy, a.symbol, a.tf, a.mode).run(once=a.once, poll_s=a.poll)


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
