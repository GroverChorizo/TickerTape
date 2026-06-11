"""Research & backtesting panel."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.text import Text

from ..state.research import ResearchQueue, ResearchJob
from .panel_base import PanelBase
from ..render.sparkline import sparkline


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
        lines: List[Any] = []
        for job in self.queue.jobs[-8:]:
            lines.append(self._format_job(job))
        text = Text()
        for item in lines:
            if isinstance(item, Text):
                text.append_text(item)
                text.append("\n")
            else:
                text.append(item + "\n")
        self.update(text)

    def _format_job(self, job: ResearchJob) -> Any:
        created = self._fmt_ts(job.created_at_ms)
        status = job.status.upper()
        dataset = job.datasets[0] if job.datasets else "n/a"
        timeframe = job.timeframes[0] if job.timeframes else "n/a"
        params = ", ".join(f"{k}={v}" for k, v in job.parameters.items()) or "none"
        header = (
            f"[{created}] {status} {job.job_type} | strategy={job.strategy_path} "
            f"dataset={dataset} tf={timeframe} params={params}"
        )
        if job.status == "completed" and job.result_path:
            result_text = self._format_result(job.result_path)
            if result_text:
                t = Text()
                t.append(header)
                t.append("\n")
                t.append_text(result_text)
                return t
        return header

    def _format_result(self, result_path: str) -> Optional[Text]:
        try:
            payload = _load_result(result_path)
        except Exception:
            return None
        curve: List[float] = payload.get("equity_curve") or []
        if len(curve) < 2:
            return None
        metrics: Dict[str, Any] = payload.get("metrics") or {}
        spark = sparkline(curve, width=40)
        total_return = metrics.get("total_return")
        max_dd = metrics.get("max_drawdown")
        sharpe = metrics.get("sharpe_ratio")
        if total_return is None and curve:
            total_return = (curve[-1] / curve[0] - 1.0) * 100.0 if curve[0] else 0.0
        if max_dd is None:
            max_dd = _compute_max_drawdown(curve)
        ret_str = f"{total_return:+.2f}%" if isinstance(total_return, (int, float)) else "n/a"
        dd_str = f"{max_dd:.2f}%" if isinstance(max_dd, (int, float)) else "n/a"
        sharpe_str = f"{sharpe:.2f}" if isinstance(sharpe, (int, float)) else "n/a"
        t = Text()
        t.append("  ", style="")
        t.append(spark, style="cyan")
        t.append(
            f"  ret={ret_str}  dd={dd_str}  sharpe={sharpe_str}",
            style="dim",
        )
        return t

    @staticmethod
    def _fmt_ts(ts_ms: int | None) -> str:
        if not ts_ms:
            return "unknown"
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M")


def _load_result(result_path: str) -> Dict[str, Any]:
    p = Path(result_path)
    if p.is_dir():
        from backtesting.job import read_result
        return read_result(str(p))
    if p.suffix.lower() == ".json" and p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Result not found: {result_path}")


def _compute_max_drawdown(curve: List[float]) -> float:
    if len(curve) < 2:
        return 0.0
    peak = curve[0]
    max_dd = 0.0
    for v in curve:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
    return max_dd
