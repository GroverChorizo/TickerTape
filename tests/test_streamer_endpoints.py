"""WS health honesty: only register streams that can actually go live.

Core market streams are keyless (HL info API) and always run. Intel streams
(whales / liquidations / events) have no keyless source, so they are only
registered when a MoonDev key is configured — otherwise the WS health bar sat
permanently degraded (the old `4/9 !`).
"""

from __future__ import annotations

from tui.providers.hyperliquid import HyperliquidStreamer


class _DL:
    def __init__(self, configured: bool):
        self._configured = configured

    @property
    def is_configured(self) -> bool:
        return self._configured


class _Direct:
    def __init__(self, dl):
        self._datalayer = dl


class _Client:
    def __init__(self, dl):
        self._direct = _Direct(dl)


class _Prov:
    def __init__(self, dl):
        self._client = _Client(dl)


def _keys(streamer) -> list[str]:
    return [e[0] for e in streamer._stream_endpoints("BTC")]


def test_core_streams_only_without_datalayer():
    keys = _keys(HyperliquidStreamer(_Prov(None)))
    assert keys == ["prices", "ticks_latest", "orderbook"]


def test_unconfigured_datalayer_stays_core_only():
    keys = _keys(HyperliquidStreamer(_Prov(_DL(False))))
    assert keys == ["prices", "ticks_latest", "orderbook"]


def test_intel_streams_added_when_configured():
    keys = _keys(HyperliquidStreamer(_Prov(_DL(True))))
    assert keys[:3] == ["prices", "ticks_latest", "orderbook"]
    assert set(keys[3:]) == {"liquidations", "whales", "events"}
