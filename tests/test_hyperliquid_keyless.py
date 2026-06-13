"""Keyless market snapshot: ticks_latest / funding via HL metaAndAssetCtxs.

Payload below is the real shape observed from the public, keyless
POST https://api.hyperliquid.xyz/info {"type":"metaAndAssetCtxs"} (trimmed to
BTC/ETH). Verifies the legacy /api/*.json GET is no longer used and that the
existing market-panel parser consumes the result.
"""

from __future__ import annotations

from providers.hyperliquid import DirectHyperliquidClient

META_AND_CTXS = [
    {
        "universe": [
            {"szDecimals": 5, "name": "BTC", "maxLeverage": 40},
            {"szDecimals": 4, "name": "ETH", "maxLeverage": 25},
        ]
    },
    [
        {
            "funding": "0.0000125",
            "openInterest": "32138.32482",
            "prevDayPx": "63494.0",
            "dayNtlVlm": "1055659895.12",
            "oraclePx": "64254.0",
            "markPx": "64221.0",
            "midPx": "64227.5",
        },
        {
            "funding": "0.0000099296",
            "openInterest": "755607.139",
            "prevDayPx": "1665.5",
            "dayNtlVlm": "259190515.04",
            "oraclePx": "1676.5",
            "markPx": "1675.8",
            "midPx": "1675.85",
        },
    ],
]


class _FakeNet:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def post(self, endpoint_key, payload):
        self.calls.append((endpoint_key, payload))
        return self._payload

    def get(self, endpoint_key, params=None):  # pragma: no cover - must not run
        raise AssertionError(f"legacy GET must not be used: {endpoint_key}")


def test_ticks_latest_from_keyless_meta_and_ctxs():
    net = _FakeNet(META_AND_CTXS)
    rows = DirectHyperliquidClient(client=net).get_json("ticks_latest")
    assert ("info", {"type": "metaAndAssetCtxs"}) in net.calls
    by = {r["symbol"]: r for r in rows}
    assert by["BTC"]["last"] == "64221.0"
    assert by["BTC"]["mid"] == "64227.5"
    assert by["BTC"]["funding"] == "0.0000125"
    assert by["BTC"]["open_interest"] == "32138.32482"
    assert by["BTC"]["rate"] == "0.0000125"  # alias the funding provider reads


def test_funding_key_uses_same_keyless_snapshot():
    net = _FakeNet(META_AND_CTXS)
    rows = DirectHyperliquidClient(client=net).get_json("funding")
    assert {r["symbol"] for r in rows} == {"BTC", "ETH"}
    assert all(r["rate"] is not None for r in rows)


def test_ticks_latest_parses_into_market_panel_records():
    from tui.feeds.market_data import _parse_top_coins

    net = _FakeNet(META_AND_CTXS)
    rows = DirectHyperliquidClient(client=net).get_json("ticks_latest")
    parsed = {p["symbol"]: p for p in _parse_top_coins(rows)}
    assert parsed["BTC"]["last"] == 64221.0  # coerced str -> float
    assert parsed["BTC"]["funding"] == 0.0000125
    assert parsed["BTC"]["open_interest"] == 32138.32482


def test_unmapped_legacy_key_still_falls_through():
    # Keys with no keyless equivalent (whales/liquidations/events) must still
    # reach the network layer (where they honestly error) — not silently 404
    # through the snapshot path.
    net = _FakeNet(META_AND_CTXS)
    try:
        DirectHyperliquidClient(client=net).get_json("whales")
    except AssertionError as exc:
        assert "legacy GET" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected fall-through to network GET")
