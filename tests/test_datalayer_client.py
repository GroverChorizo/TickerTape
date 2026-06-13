"""Tests for the vendor-neutral external data-layer client + command resolver.

No network: a fake http client is injected (mirrors test_network.py's style).
"""

from __future__ import annotations

import pytest

from providers.datalayer import (
    ApiCall,
    CommandError,
    DataLayerClient,
    DataLayerError,
    resolve_command,
)


# ── fakes ───────────────────────────────────────────────────────────────────
class _Resp:
    def __init__(self, status_code, json_obj=None, *, bad_json=False):
        self.status_code = status_code
        self._json = json_obj if json_obj is not None else {}
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("not json")
        return self._json


class _Http:
    """Returns queued responses (or raises queued exceptions) per call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        item = self._responses[len(self.calls) - 1]
        if isinstance(item, Exception):
            raise item
        return item


def _client(responses, **kw):
    return DataLayerClient(
        base_url="https://api.example.test",
        api_key="k-123",
        http_client=_Http(responses),
        sleep_fn=lambda *_a, **_k: None,
        **kw,
    )


# ── resolve_command (pure) ────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "text,path,params",
    [
        ("hip3 meta", "/api/hip3/meta", {}),
        ("hip3", "/api/hip3/meta", {}),
        ("hip3 prices", "/api/hip3/prices", {}),
        ("hip3 symbols", "/api/hip3/candles/symbols", {}),
        ("hip3 price TSLA", "/api/hip3/price/TSLA", {}),
        ("hip3 price xyz:HIMS", "/api/hip3/price/xyz:HIMS", {}),
        ("hip3 candles TSLA", "/api/hip3/candles/TSLA", {"interval": "1h"}),
        ("hip3 candles TSLA 4h", "/api/hip3/candles/TSLA", {"interval": "4h"}),
        ("hip3 ticks TSLA 24h", "/api/hip3/ticks/TSLA", {"duration": "24h"}),
        ("hip3 funding", "/api/hlp/funding/hip3", {}),
        ("hip3 liq", "/api/hip3_liquidations/stats.json", {}),
        ("hip3 liq 1h", "/api/hip3_liquidations/1h.json", {}),
        ("prices", "/api/prices", {}),
        ("price BTC", "/api/price/BTC", {}),
        ("whales", "/api/whales.json", {}),
        ("liq", "/api/liquidations/stats.json", {}),
        ("liq 4h", "/api/liquidations/4h.json", {}),
        ("smartmoney", "/api/smart_money/rankings.json", {}),
        ("funding", "/api/hlp/funding", {}),
        ("get /api/events.json", "/api/events.json", {}),
        ("get api/events.json", "/api/events.json", {}),
    ],
)
def test_resolve_command_ok(text, path, params):
    call = resolve_command(text)
    assert isinstance(call, ApiCall)
    assert call.path == path
    assert call.params == params
    assert call.label


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "bogus",
        "hip3 bogus",
        "price",
        "hip3 price",
        "hip3 price T$LA",
        "hip3 candles TSLA 2h",
        "hip3 ticks TSLA 99d",
        "liq 3h",
        "hip3 liq 12h",
        "get http://evil.example/x",
        "get https://api.example.test/x",
    ],
)
def test_resolve_command_errors(text):
    with pytest.raises(CommandError):
        resolve_command(text)


# ── client HTTP behaviour ─────────────────────────────────────────────────────
def test_get_requires_configuration():
    c = DataLayerClient(base_url="https://x.test", api_key=None)
    assert not c.is_configured
    with pytest.raises(DataLayerError):
        c.get("/api/prices")


def test_get_injects_header_and_returns_json():
    c = _client([_Resp(200, {"ok": True})])
    out = c.get("/api/hip3/meta", {"a": 1})
    assert out == {"ok": True}
    call = c._http.calls[0]
    assert call["url"] == "https://api.example.test/api/hip3/meta"
    assert call["params"] == {"a": 1}
    assert call["headers"]["X-API-Key"] == "k-123"


def test_get_retries_on_429_then_succeeds():
    c = _client([_Resp(429), _Resp(200, {"ok": 1})])
    assert c.get("/api/prices") == {"ok": 1}
    assert len(c._http.calls) == 2


def test_get_retries_on_network_error_then_succeeds():
    c = _client([RuntimeError("boom"), _Resp(200, {"ok": 1})])
    assert c.get("/api/prices") == {"ok": 1}
    assert len(c._http.calls) == 2


def test_get_raises_on_4xx_without_retry():
    c = _client([_Resp(404)])
    with pytest.raises(DataLayerError):
        c.get("/api/nope")
    assert len(c._http.calls) == 1


def test_get_auth_failure_message_mentions_key():
    c = _client([_Resp(401)])
    with pytest.raises(DataLayerError) as ei:
        c.get("/api/prices")
    assert "key" in str(ei.value).lower()


def test_get_rejects_bad_paths():
    c = _client([_Resp(200, {})])
    for bad in ("api/prices", "https://other.test/x", ""):
        with pytest.raises(DataLayerError):
            c.get(bad)
    assert c._http.calls == []  # never reached the transport


def test_get_exhausts_retries_on_5xx():
    c = _client([_Resp(500), _Resp(500), _Resp(500)], retries=3)
    with pytest.raises(DataLayerError):
        c.get("/api/prices")
    assert len(c._http.calls) == 3


def test_get_raises_on_bad_json():
    c = _client([_Resp(200, bad_json=True)])
    with pytest.raises(DataLayerError):
        c.get("/api/prices")


def test_hip3_helpers_build_expected_paths():
    c = _client([_Resp(200, {"x": 1})] * 3)
    c.hip3_meta()
    c.hip3_price("TSLA")
    c.hip3_candles("HIMS", "1h")
    urls = [call["url"] for call in c._http.calls]
    assert urls[0].endswith("/api/hip3/meta")
    assert urls[1].endswith("/api/hip3/price/TSLA")
    assert urls[2].endswith("/api/hip3/candles/HIMS")
    assert c._http.calls[2]["params"] == {"interval": "1h"}


# ── from_config ───────────────────────────────────────────────────────────────
def test_from_config_reads_key_and_base_url():
    class _Cfg:
        datalayer_base_url = "https://cfg.test"

    c = DataLayerClient.from_config(
        _Cfg(), secrets_loader=lambda: {"MOONDEV_API_KEY": "abc"}
    )
    assert c.is_configured
    assert c.base_url == "https://cfg.test"


def test_from_config_unconfigured_when_no_key(monkeypatch):
    monkeypatch.delenv("MOONDEV_API_KEY", raising=False)
    monkeypatch.delenv("DATALAYER_API_KEY", raising=False)
    c = DataLayerClient.from_config(None, secrets_loader=lambda: {})
    assert not c.is_configured
    assert c.base_url  # falls back to the default host
