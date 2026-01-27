"""Validation report screen."""

from __future__ import annotations

from typing import List

from tui.render.palette import build_text, heading_line, muted_line
from tui.ui.screens.base import BaseScreen
from validators.report import ValidationReport


class ValidationScreen(BaseScreen):
    def __init__(
        self,
        dataset: str,
        timeframe: str,
        reports: List[ValidationReport],
    ) -> None:
        super().__init__(screen_id="validation", title="Validation", context="validate")
        self._dataset = dataset
        self._timeframe = timeframe
        self._reports = reports

    def on_mount(self) -> None:
        self.set_header("Validation Report")
        self.set_status(f"Dataset: {self._dataset} | Timeframe: {self._timeframe}")
        self._render()

    def _render(self) -> None:
        lines = [
            heading_line("Validator | Errors | Warnings", self.palette),
        ]
        total_errors = 0
        total_warnings = 0
        for report in self._reports:
            total_errors += report.error_count
            total_warnings += report.warning_count
            lines.append(
                (
                    f"{report.validator:<12} | {report.error_count:<6} | {report.warning_count:<8}",
                    self.palette.text.primary,
                )
            )
        lines.append(
            muted_line(
                f"Totals: errors={total_errors} warnings={total_warnings}",
                self.palette,
            )
        )
        for report in self._reports:
            for error in report.errors[:3]:
                lines.append(
                    muted_line(f"{report.validator} error: {error}", self.palette)
                )
            for warning in report.warnings[:3]:
                lines.append(
                    muted_line(f"{report.validator} warning: {warning}", self.palette)
                )
        self.body.update(build_text(lines))
