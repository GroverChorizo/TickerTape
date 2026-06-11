"""Monte Carlo fan chart panel."""
from __future__ import annotations

from typing import Optional

from rich.text import Text

from .panel_base import PanelBase
from ..render.sparkline import sparkline


class MonteCarloPanel(PanelBase):
    """Renders P5/P50/P95 percentile sparklines from a Monte Carlo result."""

    def __init__(self) -> None:
        super().__init__(panel_id="monte_carlo", title="Monte Carlo Stress Test")
        self._percentiles: Optional[dict] = None
        self._trajectories_count: int = 0
        self._run_id: Optional[str] = None

    def set_result(self, result: object, run_id: str | None = None) -> None:
        """Accept a MonteCarloResult (or compatible duck-typed object)."""
        self._percentiles = getattr(result, "percentiles", None)
        self._trajectories_count = len(getattr(result, "trajectories", []))
        self._run_id = run_id
        self.refresh_panel()

    def clear(self) -> None:
        self._percentiles = None
        self._trajectories_count = 0
        self._run_id = None
        self.refresh_panel()

    def refresh_panel(self) -> None:
        if not self._percentiles:
            self.update_text(
                "No Monte Carlo result loaded.\n\n"
                "Run:  :mc --run-id <id>  to generate a fan chart."
            )
            return
        self._render_fan_chart()

    def _render_fan_chart(self) -> None:
        pct = self._percentiles or {}
        p95: list = pct.get("p95") or []
        p50: list = pct.get("p50") or []
        p5: list = pct.get("p5") or []
        if not p50:
            self.update_text("Insufficient data for fan chart.")
            return

        run_label = f" — run {self._run_id}" if self._run_id else ""
        t = Text()
        t.append(f"Monte Carlo Fan Chart{run_label}\n", style="bold")
        t.append("─" * 46 + "\n", style="dim")

        t.append("P95  ", style="bold green")
        t.append(sparkline(p95, width=40) + "\n", style="green")

        t.append("P50  ", style="bold white")
        t.append(sparkline(p50, width=40) + "\n", style="white")

        t.append("P5   ", style="bold red")
        t.append(sparkline(p5, width=40) + "\n", style="red")

        t.append("─" * 46 + "\n", style="dim")

        start = p50[0] if p50 else 1.0
        if not start:
            start = 1.0

        def _ret(end: float) -> str:
            return f"{(end / start - 1.0) * 100.0:+.1f}%"

        p95_end = p95[-1] if p95 else start
        p50_end = p50[-1] if p50 else start
        p5_end = p5[-1] if p5 else start

        t.append(f"Runs: {self._trajectories_count}  |  ", style="dim")
        t.append(f"P5: {_ret(p5_end)}  ", style="red")
        t.append(f"P50: {_ret(p50_end)}  ", style="white")
        t.append(f"P95: {_ret(p95_end)}", style="green")

        self.update(t)
