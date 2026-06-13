"""MoonDev Data — interactive console for the external data layer.

Opt-in, key-gated page (NOT a core feed).  A command line issues live calls
against the configured data API; HIP3 endpoints are first-class.  Core
TickerTape feeds stay keyless — see ``datadogs/`` and the ``tickertape-dev``
skill Decision Log.

Live calls run on a worker thread so the TUI never blocks.  The page makes no
network request on open; nothing is fetched until the operator types a command,
and only when a key is configured and the app is online (REAL DATA ONLY — no
synthetic fallbacks).
"""

from __future__ import annotations

from typing import Any, Optional

from textual import work
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Static

from providers.datalayer import (
    ApiCall,
    CommandError,
    DataLayerClient,
    DataLayerError,
    resolve_command,
)
from tui.ui.screens.base import BaseScreen

_CLI_ID = "moondev_cli"
_DISCLAIMER = "MoonDev Data · external data layer · informational only — not financial advice"

_HELP = """\
MoonDev Data console — type a command, press Enter

HIP3 (tokenized assets)
  hip3 meta                 all HIP3 symbols + prices
  hip3 prices               every HIP3 price
  hip3 price <SYM>          one symbol            e.g.  hip3 price TSLA
  hip3 candles <SYM> [tf]   OHLCV   tf=1m|5m|15m|1h|4h|1d   (default 1h)
  hip3 ticks <SYM> [dur]    ticks   dur=10m|1h|4h|24h|7d    (default 1h)
  hip3 funding              HIP3 funding rates
  hip3 liq [win]            HIP3 liquidations   win=stats|10m|1h|24h|7d
  hip3 symbols              symbols by category

Markets / flow
  prices                    all coin prices + funding + open interest
  price <SYM>               single coin bid/ask/mid
  whales                    recent whale trades
  liq [win]                 liquidations   win=stats|10m|1h|4h|24h|7d…
  smartmoney                smart-money rankings
  funding                   crypto funding rates
  get /api/<path>           raw GET (advanced)

  help / ?   show this          clear   clear output

Data updates daily. Key: set MOONDEV_API_KEY in your secrets file, then :reload
"""


def render_result(data: Any, *, max_rows: int = 60, max_cols: int = 9) -> Any:
    """Return a Rich renderable for an API JSON payload (table or pretty)."""
    from rich.pretty import Pretty
    from rich.table import Table

    def _records_table(records: Any, title: str = "") -> Any:
        rows = [r for r in records if isinstance(r, dict)]
        if not rows:
            return Pretty(records, max_length=max_rows)
        columns: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in columns:
                    columns.append(str(key))
        truncated_cols = len(columns) > max_cols
        columns = columns[:max_cols]
        table = Table(title=title or None, expand=True, show_lines=False)
        for col in columns:
            table.add_column(col, overflow="fold", no_wrap=False)
        if truncated_cols:
            table.add_column("…")
        for row in rows[:max_rows]:
            cells = [_fmt(row.get(col)) for col in columns]
            if truncated_cols:
                cells.append("…")
            table.add_row(*cells)
        if len(rows) > max_rows:
            table.caption = f"showing {max_rows} of {len(rows)} rows"
        return table

    if isinstance(data, list) and data and all(isinstance(x, dict) for x in data):
        return _records_table(data)
    if isinstance(data, dict):
        list_keys = [
            k
            for k, v in data.items()
            if isinstance(v, list) and v and all(isinstance(i, dict) for i in v)
        ]
        if len(list_keys) == 1:
            return _records_table(data[list_keys[0]], title=str(list_keys[0]))
    return Pretty(data, max_length=max_rows, max_string=160)


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:,.6g}"
    return str(value)


class MoonDevScreen(BaseScreen):
    """Command console over the external data layer (HIP3 + market/flow)."""

    def __init__(self, client: Optional[DataLayerClient] = None) -> None:
        super().__init__(screen_id="moondev", title="MoonDev Data", context="moondev")
        self._client = client
        # markup=False: status/help are literal text — '[offline]', '[error]',
        # etc. must not be parsed as Rich markup tags (which would eat them).
        self._meta = Static("", id="moondev_meta", markup=False)
        self._results = Static(_HELP, id="moondev_results", markup=False)
        self._cli = Input(
            placeholder="MoonDev API ▸  hip3 price TSLA   (type 'help')", id=_CLI_ID
        )
        self._body = Vertical(
            Static(_DISCLAIMER, id="moondev_disclaimer", markup=False),
            self._meta,
            Vertical(self._results, id="moondev_results_wrap"),
            self._cli,
            id="screen_body",
        )
        self.body = self._body

    def compose(self):
        with Vertical(id="screen_root"):
            yield self.header
            yield self.status
            yield self.tab_carousel
            with Horizontal(id="content_row"):
                yield self.sidebar
                yield self._body
            yield self.tabbar
            yield self.command_bar

    def on_mount(self) -> None:
        self.set_header("MoonDev Data")
        self.set_status(
            "Live console over the external data layer. HIP3 is first-class. "
            "Type 'help'. Updates daily; this is not the primary feed."
        )
        self._refresh_meta()

    def on_show(self) -> None:
        super().on_show()
        self._refresh_meta()
        try:
            self._cli.focus()
        except Exception:
            pass

    # ── client / mode ──────────────────────────────────────────────────────
    def _get_client(self) -> DataLayerClient:
        if self._client is None:
            self._client = DataLayerClient.from_config(getattr(self.app, "config", None))
        return self._client

    def _is_offline(self) -> bool:
        return getattr(getattr(self.app, "config", None), "mode", None) == "offline_demo"

    def _refresh_meta(self) -> None:
        if self._is_offline():
            self._meta.update("[offline] live calls disabled — start TickerTape online to query")
            return
        client = self._get_client()
        if not client.is_configured:
            self._meta.update("[not configured] set MOONDEV_API_KEY in your secrets file, then :reload")
            return
        self._meta.update(f"ready · {client.base_url} · updates daily")

    # ── command line ────────────────────────────────────────────────────────
    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Only intercept this page's CLI; the global command bar keeps working.
        if event.input.id != _CLI_ID:
            super().on_input_submitted(event)
            return
        event.stop()
        text = event.value.strip()
        self._cli.value = ""
        if text:
            self._run(text)

    def _run(self, text: str) -> None:
        low = text.lower()
        if low in {"help", "?"}:
            self._results.update(_HELP)
            self._meta.update("help")
            return
        if low == "clear":
            self._results.update("")
            self._meta.update("cleared")
            return
        try:
            call = resolve_command(text)
        except CommandError as exc:
            self._meta.update(f"[error] {exc}")
            return
        if self._is_offline():
            self._meta.update("[offline] live calls disabled — start TickerTape online to query")
            return
        client = self._get_client()
        if not client.is_configured:
            self._meta.update("[not configured] set MOONDEV_API_KEY in your secrets file, then :reload")
            return
        self._meta.update(f"… {call.label or call.path}")
        self._fetch(call)

    @work(thread=True, exclusive=True, group="moondev_fetch")
    def _fetch(self, call: ApiCall) -> None:
        client = self._get_client()
        try:
            data = client.get(call.path, call.params)
        except DataLayerError as exc:
            self.app.call_from_thread(self._show_error, call, str(exc))
            return
        except Exception as exc:  # defensive: a worker must never crash the app
            self.app.call_from_thread(self._show_error, call, f"{type(exc).__name__}: {exc}")
            return
        self.app.call_from_thread(self._show_result, call, data)

    def _show_result(self, call: ApiCall, data: Any) -> None:
        try:
            self._results.update(render_result(data))
        except Exception as exc:  # rendering must not break the page
            self._results.update(f"(unrenderable payload: {type(exc).__name__})")
        self._meta.update(f"ok · {call.label or call.path}")

    def _show_error(self, call: ApiCall, message: str) -> None:
        self._results.update(f"[error] {call.label or call.path}\n\n{message}")
        self._meta.update(f"[error] {call.label or call.path}")
