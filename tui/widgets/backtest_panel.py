"""Research & backtesting panel."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..state.research import ResearchQueue, ResearchJob
from .panel_base import PanelBase


class BacktestPanel(PanelBase):
    def __init__(self, queue: ResearchQueue) -> None:
        super().__init__(panel_id="research", title="Research & Backtesting")
        self.queue = queue

    def refresh_panel(self) -> None:
        if not self.queue.jobs:
            self.update_text(
                "No research jobs queued. Use the command bar for /backtest, /montecarlo, or /walkforward runs."
            )
            return
        lines: List[str] = []
        for job in self.queue.jobs[-8:]:
            lines.append(self._format_job(job))
        self.update_text("\n".join(lines))

    def _format_job(self, job: ResearchJob) -> str:
        created = self._fmt_ts(job.created_at_ms)
        status = job.status.upper()
        dataset = job.datasets[0] if job.datasets else "n/a"
        timeframe = job.timeframes[0] if job.timeframes else "n/a"
        params = ", ".join(f"{k}={v}" for k, v in job.parameters.items()) or "none"
        return (
            f"[{created}] {status} {job.job_type} | strategy={job.strategy_path} "
            f"dataset={dataset} tf={timeframe} params={params}"
        )

    @staticmethod
    def _fmt_ts(ts_ms: int | None) -> str:
        if not ts_ms:
            return "unknown"
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M")
