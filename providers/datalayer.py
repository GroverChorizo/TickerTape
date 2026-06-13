"""Vendor-neutral external data-layer client (configurable base URL + API key).

Point it at any compatible data API via ``base_url`` and authenticate with an
``X-API-Key`` header.  The TickerTape "MoonDev Data" console
(``tui/ui/screens/moondev.py``) uses it to query the data service the operator
has lifetime access to.

This client backs the optional, opt-in console page ONLY.  The primary
TickerTape feeds stay keyless (Hyperliquid info API / ccxt via ``datadogs``);
this is never the main data path.  See the ``tickertape-dev`` skill Decision
Log for the rationale behind this sanctioned exception to the keyless
direction.

Security:
  * The API key is sent in the ``X-API-Key`` header, never in the URL/query.
  * Logs carry path + status + elapsed only — never the key, params, or body.
  * Arbitrary-path queries are constrained to the configured host: a path must
    start with ``/`` and may not contain a scheme/host (no SSRF to other hosts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
import os
import re
import time

from backend.logging_config import get_logger

logger = get_logger(__name__)

# Default deployment the operator has access to. Overridable via config/env so
# the client itself stays vendor-neutral and testable.
DEFAULT_BASE_URL = "https://api.moondev.com"
DEFAULT_TIMEOUT = 10.0
DEFAULT_RETRIES = 3
BACKOFF_FACTOR = 0.5  # seconds, exponential

# Secrets/env keys consulted, in order, for the API key.
API_KEY_NAMES = ("MOONDEV_API_KEY", "DATALAYER_API_KEY")

# Validation sets (mirror the API's accepted values).
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9:_.-]{1,32}$")
_CANDLE_INTERVALS = {"1m", "5m", "15m", "1h", "4h", "1d"}
_TICK_DURATIONS = {"10m", "1h", "4h", "24h", "7d"}
_LIQ_WINDOWS = {"stats", "10m", "1h", "4h", "12h", "24h", "2d", "7d", "14d", "30d"}
_HIP3_LIQ_WINDOWS = {"stats", "10m", "1h", "24h", "7d"}


class DataLayerError(RuntimeError):
    """Request failed, or the client is not configured."""


class CommandError(ValueError):
    """A console command could not be parsed/validated."""


@dataclass
class ApiCall:
    """A resolved, validated request (path + query params + display label)."""

    path: str
    params: Dict[str, Any] = field(default_factory=dict)
    label: str = ""


class DataLayerClient:
    """HTTP client for the external data layer.

    Inject ``http_client`` (any object with ``get(url, params=, headers=)``
    returning an object exposing ``.status_code`` and ``.json()``) for tests;
    a real :mod:`httpx` client is created lazily otherwise.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        http_client: Optional[Any] = None,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._api_key = (api_key or "").strip() or None
        self._timeout = timeout
        self._retries = max(1, int(retries))
        self._sleep = sleep_fn
        self._http = http_client

    @property
    def is_configured(self) -> bool:
        return self._api_key is not None

    @classmethod
    def from_config(
        cls,
        config: Any = None,
        *,
        secrets_loader: Optional[Callable[[], Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> "DataLayerClient":
        """Build from a TuiConfig-like object + the secrets file.

        ``base_url`` comes from ``config.datalayer_base_url`` (falls back to
        :data:`DEFAULT_BASE_URL`); the API key comes from the secrets file /
        environment.  Neither is logged.
        """
        base_url = getattr(config, "datalayer_base_url", None) if config is not None else None
        api_key = _load_api_key(secrets_loader)
        return cls(base_url=base_url, api_key=api_key, **kwargs)

    def _client(self) -> Any:
        if self._http is None:
            import httpx

            self._http = httpx.Client(timeout=self._timeout)
        return self._http

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET ``path`` against the configured host and return parsed JSON.

        Retries 429/5xx and transient network errors with exponential backoff;
        4xx (other than 429) raise immediately.  Never logs the key or body.
        """
        if not self.is_configured:
            raise DataLayerError(
                "API key not configured. Add MOONDEV_API_KEY to your secrets "
                "file, then reload."
            )
        if not isinstance(path, str) or not path.startswith("/") or "://" in path:
            raise DataLayerError(f"invalid path {path!r} (must be a host-relative '/...' path)")

        url = f"{self.base_url}{path}"
        headers = {"X-API-Key": self._api_key}
        client = self._client()
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._retries + 1):
            start = time.time()
            try:
                resp = client.get(url, params=params or {}, headers=headers)
            except Exception as exc:  # transient transport error → retry
                last_exc = exc
                logger.warning(
                    {
                        "event": "datalayer_network_error",
                        "path": path,
                        "attempt": attempt,
                        "err": type(exc).__name__,
                    }
                )
                self._sleep(BACKOFF_FACTOR * (2 ** (attempt - 1)))
                continue

            status = int(getattr(resp, "status_code", 0))
            logger.info(
                {
                    "event": "datalayer_request",
                    "path": path,
                    "status": status,
                    "elapsed_ms": int((time.time() - start) * 1000),
                    "attempt": attempt,
                }
            )

            if status == 429 or 500 <= status < 600:
                last_exc = DataLayerError(f"server returned {status}")
                self._sleep(BACKOFF_FACTOR * (2 ** (attempt - 1)))
                continue
            if status in (401, 403):
                raise DataLayerError(
                    f"API rejected the key (HTTP {status}). Check MOONDEV_API_KEY."
                )
            if 400 <= status < 500:
                raise DataLayerError(f"request failed (HTTP {status}) for {path}")
            try:
                return resp.json()
            except Exception as exc:  # malformed body
                raise DataLayerError(f"invalid JSON from {path}: {exc}") from exc

        raise DataLayerError(
            f"{path} failed after {self._retries} attempt(s): {last_exc}"
        )

    def close(self) -> None:
        if self._http is not None:
            try:
                self._http.close()
            except Exception:
                pass

    # ── HIP3 helpers (first-class) ─────────────────────────────────────────
    def hip3_meta(self) -> Any:
        return self.get("/api/hip3/meta")

    def hip3_prices(self) -> Any:
        return self.get("/api/hip3/prices")

    def hip3_symbols(self) -> Any:
        return self.get("/api/hip3/candles/symbols")

    def hip3_price(self, symbol: str) -> Any:
        return self.get(f"/api/hip3/price/{_symbol(symbol)}")

    def hip3_candles(self, symbol: str, interval: str = "1h") -> Any:
        return self.get(
            f"/api/hip3/candles/{_symbol(symbol)}", {"interval": _interval(interval)}
        )

    def hip3_ticks(self, symbol: str, duration: str = "1h") -> Any:
        return self.get(
            f"/api/hip3/ticks/{_symbol(symbol)}", {"duration": _duration(duration)}
        )

    def hip3_funding(self) -> Any:
        return self.get("/api/hlp/funding/hip3")

    def hip3_liquidations(self, window: str = "stats") -> Any:
        return self.get(f"/api/hip3_liquidations/{_hip3_liq_window(window)}.json")


# ── shared validators ──────────────────────────────────────────────────────
def _symbol(value: str) -> str:
    v = (value or "").strip()
    if not _SYMBOL_RE.match(v):
        raise CommandError(f"invalid symbol {value!r}")
    return v


def _interval(value: str) -> str:
    v = (value or "").strip().lower()
    if v not in _CANDLE_INTERVALS:
        raise CommandError(f"interval must be one of {sorted(_CANDLE_INTERVALS)}")
    return v


def _duration(value: str) -> str:
    v = (value or "").strip().lower()
    if v not in _TICK_DURATIONS:
        raise CommandError(f"duration must be one of {sorted(_TICK_DURATIONS)}")
    return v


def _liq_window(value: str) -> str:
    v = (value or "").strip().lower()
    if v not in _LIQ_WINDOWS:
        raise CommandError(f"window must be one of {sorted(_LIQ_WINDOWS)}")
    return v


def _hip3_liq_window(value: str) -> str:
    v = (value or "").strip().lower()
    if v not in _HIP3_LIQ_WINDOWS:
        raise CommandError(f"window must be one of {sorted(_HIP3_LIQ_WINDOWS)}")
    return v


def _raw_path(value: str) -> str:
    v = (value or "").strip()
    if "://" in v or v.startswith("//"):
        raise CommandError("get accepts a host-relative path (e.g. /api/prices), not a URL")
    if not v.startswith("/"):
        v = "/" + v
    return v


def _load_api_key(secrets_loader: Optional[Callable[[], Dict[str, str]]] = None) -> Optional[str]:
    """Read the API key from the secrets file (then process env). Never logged."""
    data: Dict[str, str] = {}
    try:
        if secrets_loader is None:
            from backend.secrets import load_secrets as secrets_loader  # type: ignore
        data = secrets_loader() or {}
    except Exception:
        data = {}
    for name in API_KEY_NAMES:
        val = (data.get(name) or os.environ.get(name) or "").strip()
        if val:
            return val
    return None


# ── console command resolution ───────────────────────────────────────────--
def resolve_command(text: str) -> ApiCall:
    """Map a console command string to a validated :class:`ApiCall`.

    Pure and side-effect free so it can be unit-tested without the TUI or
    network.  Raises :class:`CommandError` on anything it can't validate.
    """
    parts = (text or "").strip().split()
    if not parts:
        raise CommandError("empty command")
    head = parts[0].lower()
    rest = parts[1:]

    if head == "hip3":
        return _resolve_hip3(rest)
    if head == "prices":
        return ApiCall("/api/prices", {}, "prices")
    if head == "price":
        if not rest:
            raise CommandError("usage: price <SYMBOL>")
        return ApiCall(f"/api/price/{_symbol(rest[0])}", {}, f"price {rest[0].upper()}")
    if head == "whales":
        return ApiCall("/api/whales.json", {}, "whales")
    if head == "liq":
        window = _liq_window(rest[0]) if rest else "stats"
        return ApiCall(f"/api/liquidations/{window}.json", {}, f"liquidations {window}")
    if head in {"smartmoney", "smart"}:
        return ApiCall("/api/smart_money/rankings.json", {}, "smart money rankings")
    if head == "funding":
        return ApiCall("/api/hlp/funding", {}, "funding (crypto)")
    if head == "get":
        if not rest:
            raise CommandError("usage: get /api/<path>")
        return ApiCall(_raw_path(rest[0]), {}, f"GET {rest[0]}")
    raise CommandError(f"unknown command {head!r} — type 'help'")


def _resolve_hip3(rest: list[str]) -> ApiCall:
    sub = rest[0].lower() if rest else "meta"
    args = rest[1:]

    if sub == "meta":
        return ApiCall("/api/hip3/meta", {}, "HIP3 meta")
    if sub == "prices":
        return ApiCall("/api/hip3/prices", {}, "HIP3 prices")
    if sub == "symbols":
        return ApiCall("/api/hip3/candles/symbols", {}, "HIP3 symbols")
    if sub == "price":
        if not args:
            raise CommandError("usage: hip3 price <SYMBOL>")
        return ApiCall(f"/api/hip3/price/{_symbol(args[0])}", {}, f"HIP3 price {args[0]}")
    if sub == "candles":
        if not args:
            raise CommandError("usage: hip3 candles <SYMBOL> [interval]")
        interval = _interval(args[1]) if len(args) > 1 else "1h"
        return ApiCall(
            f"/api/hip3/candles/{_symbol(args[0])}",
            {"interval": interval},
            f"HIP3 candles {args[0]} {interval}",
        )
    if sub == "ticks":
        if not args:
            raise CommandError("usage: hip3 ticks <SYMBOL> [duration]")
        duration = _duration(args[1]) if len(args) > 1 else "1h"
        return ApiCall(
            f"/api/hip3/ticks/{_symbol(args[0])}",
            {"duration": duration},
            f"HIP3 ticks {args[0]} {duration}",
        )
    if sub == "funding":
        return ApiCall("/api/hlp/funding/hip3", {}, "HIP3 funding")
    if sub == "liq":
        window = _hip3_liq_window(args[0]) if args else "stats"
        return ApiCall(
            f"/api/hip3_liquidations/{window}.json", {}, f"HIP3 liquidations {window}"
        )
    raise CommandError(f"unknown hip3 subcommand {sub!r} — type 'help'")
