"""Generic panel for displaying raw JSON payloads."""

from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.pretty import Pretty

from tui.feeds.base import FeedResult, FeedStatus, _as_status
from tui.render.palette import build_text, last_updated_line, muted_line, panel_header
from .panel_base import PanelBase


class RawJsonPanel(PanelBase):
    def __init__(self, panel_id: str, title: str, *, max_items: int = 20) -> None:
        super().__init__(panel_id=panel_id, title=title)
        self.feed_result = FeedResult(status="loading")
        self._max_items = max_items

    def update_feed(self, result: FeedResult) -> None:
        self.feed_result = result
        self.refresh_panel()

    def refresh_panel(self) -> None:
        status = _as_status(self.feed_result.status)
        if status == FeedStatus.LOADING:
            self._render_loading()
            return
        if status in {FeedStatus.ERROR, FeedStatus.DISCONNECTED} and not self.feed_result.data:
            self._render_error(self.feed_result.error or "Unknown error")
            return
        if status == FeedStatus.EMPTY and not self.feed_result.data:
            self._render_empty("No data yet.")
            return
        self._render_data(self.feed_result.data, status, self.feed_result.updated_ts_ms)

    def _render_loading(self) -> None:
        self.set_status_class(FeedStatus.LOADING.value)
        lines = [
            panel_header(self.title, FeedStatus.LOADING.value, self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line("Loading data...", self.palette),
        ]
        self.update_text(build_text(lines))

    def _render_empty(self, reason: str) -> None:
        self.set_status_class(FeedStatus.EMPTY.value)
        lines = [
            panel_header(self.title, FeedStatus.EMPTY.value, self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line(reason, self.palette),
        ]
        self.update_text(build_text(lines))

    def _render_error(self, error: str) -> None:
        self.set_status_class(FeedStatus.ERROR.value)
        lines = [
            panel_header(self.title, FeedStatus.ERROR.value, self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            (error, self.palette.text.primary),
        ]
        self.update_text(build_text(lines))

    def _render_data(
        self, payload: Any, status: FeedStatus, updated_ts_ms: int | None
    ) -> None:
        self.set_status_class(
            FeedStatus.DISCONNECTED.value
            if status == FeedStatus.DISCONNECTED
            else FeedStatus.OK.value
        )
        header = panel_header(
            self.title,
            FeedStatus.DISCONNECTED.value
            if status == FeedStatus.DISCONNECTED
            else FeedStatus.OK.value,
            self.palette,
        )
        # Convert tuple-based helper output to Rich Text before grouping.
        # Passing raw tuple values into Group triggers NotRenderableError.
        updated = build_text([last_updated_line(updated_ts_ms, self.palette)])
        trimmed = _trim_payload(payload, self._max_items)
        body = Pretty(trimmed, max_depth=3, expand_all=False)
        self.update(Group(header, updated, body))


def _trim_payload(payload: Any, max_items: int) -> Any:
    if isinstance(payload, list):
        if len(payload) <= max_items:
            return payload
        return payload[:max_items] + [
            {"_truncated": f"+{len(payload) - max_items} items"}
        ]
    if isinstance(payload, dict):
        trimmed: dict[str, Any] = {}
        for key, value in payload.items():
            trimmed[key] = _trim_payload(value, max_items)
        return trimmed
    return payload
