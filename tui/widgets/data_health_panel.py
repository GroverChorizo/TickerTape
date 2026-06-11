"""Data health panel: per-CSV freshness/gap table for the datadogs store.

Mirrors `python -m datadogs health` — same validate logic, same thresholds —
so the panel and the CLI can never disagree about what "healthy" means.
The scan reads real CSVs and may take a few hundred ms; run it in a worker
thread (`scan_health` is widget-free on purpose) and hand rows to the panel.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from rich.text import Text

from .panel_base import PanelBase


@dataclass
class HealthRow:
    file: str
    rows: int
    age_bars: float
    gaps: int
    last_bar: str
    status: str  # OK | STALE | ERROR
    detail: str = ""


def scan_health() -> List[HealthRow]:
    """Validate every CSV in the datadogs store. Thread-safe, no UI access."""
    from datadogs.common import (TIMEFRAME_MS, iso, now_ms, read_csv,
                                 read_meta, validate)
    from datadogs.config import data_dir

    out: List[HealthRow] = []
    for p in sorted(data_dir().glob("*.csv")):
        try:
            if p.name.endswith("-funding.csv"):
                import pandas as pd

                df = pd.read_csv(p)
                last = int(df["ts"].max()) if len(df) else 0
                age_h = (now_ms() - last) / 3_600_000 if last else float("inf")
                status = "OK" if age_h <= 3 else "STALE"
                out.append(HealthRow(p.name, len(df), age_h, 0,
                                     iso(last) if last else "—", status,
                                     detail="funding (age in hours)"))
                continue
            stem = p.stem  # BTC-15m or BTC.coinbase-15m
            _, tfname = stem.rsplit("-", 1)
            if tfname not in TIMEFRAME_MS:
                continue
            df = read_csv(p)
            rep = validate(df, tfname, path=str(p),
                           source=read_meta(p).get("source", ""))
            age = ((now_ms() - rep.ts_max) / TIMEFRAME_MS[tfname]
                   if rep.rows else float("inf"))
            if not rep.ok:
                status, detail = "ERROR", "; ".join(rep.errors[:2])
            elif age > 2:
                status, detail = "STALE", ""
            else:
                status, detail = "OK", ""
            out.append(HealthRow(p.name, rep.rows, age, len(rep.gaps),
                                 iso(rep.ts_max) if rep.rows else "—",
                                 status, detail))
        except Exception as exc:  # a broken file must show up, not crash the panel
            out.append(HealthRow(p.name, 0, float("inf"), 0, "—", "ERROR", str(exc)))
    return out


_STATUS_STYLE = {"OK": "green", "STALE": "yellow", "ERROR": "bold red"}


class DataHealthPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="ops_data_health", title="Data Health")

    def show_scanning(self) -> None:
        self.update_text("Scanning data store…")

    def show_rows(self, rows: List[HealthRow]) -> None:
        if not rows:
            self.update_text(
                "No CSV files in the data store.\n\n"
                "Fetch real data first:  python -m datadogs fetch-all\n"
                "(Never substitute synthetic data.)"
            )
            self.set_status_class("error")
            return
        worst = ("ERROR" if any(r.status == "ERROR" for r in rows)
                 else "STALE" if any(r.status == "STALE" for r in rows) else "OK")
        self.set_status_class("ok" if worst == "OK" else "error")

        t = Text()
        hdr = f"{'file':<24}{'rows':>8}  {'age':>7}  {'gaps':>4}  {'last bar (UTC)':<18}{'status':<7}\n"
        t.append(hdr, style="bold")
        t.append("─" * len(hdr) + "\n", style="dim")
        for r in rows:
            age = "∞" if r.age_bars == float("inf") else f"{r.age_bars:.1f}"
            unit = "h" if r.detail.startswith("funding") else "b"
            t.append(f"{r.file:<24}{r.rows:>8,}  {age + unit:>7}  {r.gaps:>4}  {r.last_bar:<18}")
            t.append(f"{r.status:<7}", style=_STATUS_STYLE.get(r.status, ""))
            if r.detail and not r.detail.startswith("funding"):
                t.append(f"  {r.detail}", style="dim")
            t.append("\n")
        t.append("\nage: b = bars (STALE > 2), h = hours (funding, STALE > 3). "
                 "Gaps are reported, never filled.", style="dim")
        self.update(t)
