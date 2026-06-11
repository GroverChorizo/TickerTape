"""Research & Backtesting screen.

Accessible from every profile via the sidebar "Research" entry or the
`:research` / `:jobs` commands.  Users can review queued/completed backtest
jobs, see how to submit new runs from the command bar, and check what
exported datasets are available for feeding into strategy scripts.
"""

from __future__ import annotations

from typing import List

from textual.containers import Horizontal, Vertical
from textual.widgets import Static, TabbedContent, TabPane

from tui.ui.screens.base import BaseScreen
from tui.widgets.backtest_panel import BacktestPanel
from tui.widgets.monte_carlo_panel import MonteCarloPanel
from tui.state.research import ResearchQueue


_RUN_HELP = """\
Run a backtest from the command bar
─────────────────────────────────────────────────────
  :backtest run <strategy_file.py>
      Execute a strategy against local snapshot data.
      Results are saved to ~/.ticker_tape/jobs/<run_id>/

  :mc --run-id <id> [--runs N] [--seed N]
      Monte Carlo stress-test a completed backtest run.

  :jobs list
      List recent runs with status, strategy, and dates.

  :jobs show <id>
      Show full metadata and metrics for a single run.

  :bt_export   /   :mc_export
      (coming soon) Export results to CSV/JSON.

─────────────────────────────────────────────────────
Workflow: export panel data with  :export <panel> csv
then feed the file into your strategy script as the
dataset argument.
"""


class ResearchScreen(BaseScreen):
    """Jobs queue, run instructions, dataset export overview, and MC fan chart."""

    def __init__(self) -> None:
        super().__init__(
            screen_id="research",
            title="Research",
            context="research",
        )
        self._queue = ResearchQueue()
        self.backtest_panel = BacktestPanel(self._queue)
        self.mc_panel = MonteCarloPanel()
        self._run_info = Static(_RUN_HELP, id="research_run_info")
        self._export_info = Static("", id="research_export_info")
        self._tabs = TabbedContent(id="research_tabs")
        self._body = Vertical(id="screen_body")
        self.body = self._body

    # ── layout ────────────────────────────────────────────────────────────────

    def compose(self):
        with Vertical(id="screen_root"):
            yield self.header
            yield self.status
            yield self.tab_carousel
            with Horizontal(id="content_row"):
                yield self.sidebar
                with self._body:
                    with self._tabs:
                        with TabPane("Jobs", id="research_tab_jobs"):
                            yield self.backtest_panel
                        with TabPane("Run", id="research_tab_run"):
                            yield self._run_info
                        with TabPane("Export", id="research_tab_export"):
                            yield self._export_info
                        with TabPane("Stress Test", id="research_tab_mc"):
                            yield self.mc_panel
            yield self.tabbar
            yield self.command_bar

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self.set_header("Research | Backtesting")
        self.set_status(
            "Jobs tab: recent runs.  Run tab: command reference.  "
            "Export tab: available datasets.  Stress Test tab: MC fan chart."
        )
        self._refresh_jobs()
        self._refresh_export_info()
        self.set_interval(5.0, self._refresh_jobs)

    def on_show(self) -> None:
        super().on_show()
        self._refresh_jobs()
        self._refresh_export_info()
        self._load_pending_mc()

    # ── Monte Carlo ───────────────────────────────────────────────────────────

    def show_mc_result(self, result: object, run_id: str | None = None) -> None:
        """Display a MC result in the Stress Test tab and switch to it."""
        self.mc_panel.set_result(result, run_id)
        try:
            self._tabs.active = "research_tab_mc"
        except Exception:
            pass

    def _load_pending_mc(self) -> None:
        """Pick up any pending MC result stored on the app."""
        app = getattr(self, "app", None)
        if app is None:
            return
        pending = getattr(app, "_pending_mc_result", None)
        if pending is not None:
            run_id, mc_result = pending
            self.show_mc_result(mc_result, run_id)
            app._pending_mc_result = None

    # ── data refresh ──────────────────────────────────────────────────────────

    def _refresh_jobs(self) -> None:
        try:
            self._queue._load()
        except Exception:
            pass
        self.backtest_panel.refresh_panel()

    def _refresh_export_info(self) -> None:
        lines: List[str] = []
        try:
            from backend.storage import DatasetRegistry
            from tui.state.datasets import load_datasets

            data_root = getattr(self.app.config, "data_root", None)
            if data_root is None:
                raise ValueError("no data_root")
            registry = DatasetRegistry(path=data_root / "_registry.json")
            datasets = load_datasets(registry)
            if datasets:
                lines.append("Available datasets\n")
                lines.append("─" * 40 + "\n")
                for name, info in list(datasets.items())[:20]:
                    tfs = ", ".join(sorted(info.timeframes)) if info.timeframes else "n/a"
                    lines.append(f"  {name}\n    timeframes: {tfs}\n")
                lines.append(
                    "\nUse  :backtest run <file.py>  with the dataset name\n"
                    "as the --dataset argument in your strategy script.\n"
                )
            else:
                lines.append(
                    "No datasets found.\n\n"
                    "Export panel data first with  :export <panel> csv\n"
                    "Exports land in  data/exports/  as CSV or JSON files.\n"
                )
        except Exception:
            lines.append(
                "Could not load dataset registry.\n\n"
                "Export panel data with  :export <panel> csv  to create\n"
                "files that your strategy scripts can consume.\n"
            )
        self._export_info.update("".join(lines))
