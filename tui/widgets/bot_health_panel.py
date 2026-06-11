"""Bot health panel: heartbeats from state/<bot>.json + kill-switch status.

Read-only consumer of the Bot–TickerTape Interface Contract. Thresholds per
the contract: green < 2 bars of data lag, yellow < 5, red otherwise; the
wall-clock heartbeat uses 2/10 minutes since bots cycle at least once a minute.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from rich.text import Text

from .panel_base import PanelBase

STATE_DIR = Path("state")
KILL_PATH = STATE_DIR / "KILL"


def read_bot_states(state_dir: Path = STATE_DIR) -> List[Dict[str, Any]]:
    """Parse every bot state file. Unreadable files surface as error entries."""
    if not state_dir.exists():
        return []
    out: List[Dict[str, Any]] = []
    for p in sorted(state_dir.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as exc:
            out.append({"bot_id": p.stem, "_error": str(exc)})
    return out


def _lag_style(lag_bars: Any) -> str:
    if not isinstance(lag_bars, (int, float)):
        return "red"
    return "green" if lag_bars < 2 else "yellow" if lag_bars < 5 else "red"


def _alive_style(age_s: float) -> str:
    return "green" if age_s < 120 else "yellow" if age_s < 600 else "red"


class BotHealthPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="ops_bot_health", title="Bot Health")

    def refresh_panel(self) -> None:
        t = Text()
        if KILL_PATH.exists():
            t.append("  KILL SWITCH ACTIVE  ", style="bold white on red")
            t.append(f"  {KILL_PATH} exists — all bots stop on their next loop.\n\n")
        states = read_bot_states()
        if not states:
            t.append(
                f"No bots registered — no state files in {STATE_DIR}\\.\n\n"
                "Each running bot writes an atomic heartbeat to\n"
                "state/<bot_id>.json every cycle. An empty panel means\n"
                "no bot process is (or was) running. Nothing is simulated."
            )
            self.update(t)
            return
        now_ms = time.time() * 1000
        hdr = (f"{'bot':<24}{'mode':<8}{'alive':<10}{'lag':<6}"
               f"{'err 24h':<8}{'position':<20}\n")
        t.append(hdr, style="bold")
        t.append("─" * len(hdr) + "\n", style="dim")
        for st in states:
            bot = str(st.get("bot_id", "?"))
            if "_error" in st:
                t.append(f"{bot:<24}")
                t.append(f"unreadable state file: {st['_error']}\n", style="bold red")
                continue
            alive_at = st.get("alive_at")
            age_s = ((now_ms - alive_at) / 1000
                     if isinstance(alive_at, (int, float)) else float("inf"))
            alive = (f"{age_s:.0f}s ago" if age_s < 600
                     else f"{age_s / 60:.0f}m ago" if age_s != float("inf") else "never")
            lag = st.get("data_lag_bars")
            pos = st.get("open_position")
            pos_txt = "flat" if pos in (None, "", {}) else json.dumps(pos)[:18]
            t.append(f"{bot:<24}{str(st.get('mode', '?')):<8}")
            t.append(f"{alive:<10}", style=_alive_style(age_s))
            t.append(f"{str(lag if lag is not None else '—'):<6}", style=_lag_style(lag))
            t.append(f"{str(st.get('errors_24h', '—')):<8}{pos_txt:<20}\n")
        t.append("\nlag: green <2 bars, yellow <5, red ≥5 · heartbeat: "
                 "green <2m, yellow <10m · kill: create state\\KILL", style="dim")
        self.update(t)
