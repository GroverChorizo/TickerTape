"""Signal tape panel: live feed off signals/signals.jsonl.

Read-only consumer of the Bot–TickerTape Interface Contract (vault,
04_Infrastructure). Bots append one JSON object per line; this panel tails
the file. No file → honest empty state, never fabricated rows.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from rich.text import Text

from .panel_base import PanelBase

SIGNALS_PATH = Path("signals") / "signals.jsonl"

_EVENT_STYLE = {
    "entry_signal": "bold green",
    "exit_signal": "bold cyan",
    "no_trade_heartbeat": "dim",
    "error": "bold red",
}


def read_tail(path: Path = SIGNALS_PATH, n: int = 50) -> List[Dict[str, Any]]:
    """Last n parsed signal events, oldest→newest. Malformed lines are kept
    as error rows — a corrupt tape must be visible, not skipped."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-n:]
    events: List[Dict[str, Any]] = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            events.append(json.loads(ln))
        except json.JSONDecodeError:
            events.append({"event": "error", "strategy": "<malformed line>",
                           "raw": ln[:60]})
    return events


def _fmt_ts(ts_ms: Any) -> str:
    try:
        return datetime.fromtimestamp(int(ts_ms) / 1000,
                                      tz=timezone.utc).strftime("%m-%d %H:%M")
    except (TypeError, ValueError, OSError):
        return "—"


class SignalTapePanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="ops_signal_tape", title="Signal Tape")

    def refresh_panel(self) -> None:
        events = read_tail()
        if not events:
            self.update_text(
                f"No signals yet — {SIGNALS_PATH} not found or empty.\n\n"
                "The tape fills when a bot runs in shadow mode and appends\n"
                "signal events per the Bot–TickerTape Interface Contract.\n"
                "Nothing is shown that a bot did not actually emit."
            )
            return
        t = Text()
        hdr = (f"{'bar ts (UTC)':<13}{'strategy':<22}{'sym':<10}{'tf':<5}"
               f"{'event':<20}{'side':<6}{'mode':<8}{'conf':>5}\n")
        t.append(hdr, style="bold")
        t.append("─" * len(hdr) + "\n", style="dim")
        for ev in reversed(events):  # newest first
            event = str(ev.get("event", "?"))
            conf = ev.get("confidence")
            t.append(f"{_fmt_ts(ev.get('ts')):<13}")
            t.append(f"{str(ev.get('strategy', '?')):<22}")
            t.append(f"{str(ev.get('symbol', '—')):<10}{str(ev.get('tf', '—')):<5}")
            t.append(f"{event:<20}", style=_EVENT_STYLE.get(event, ""))
            t.append(f"{str(ev.get('side', '—')):<6}{str(ev.get('mode', '—')):<8}")
            t.append(f"{conf:>5.2f}" if isinstance(conf, (int, float)) else f"{'—':>5}")
            t.append("\n")
        t.append(f"\n{len(events)} most recent events · append-only · "
                 f"tail -f {SIGNALS_PATH}", style="dim")
        self.update(t)
