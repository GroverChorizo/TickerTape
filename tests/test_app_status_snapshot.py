from __future__ import annotations

from tickertape.core.alerts import AlertEvent, AlertSeverity
from tui.app import TickerTapeApp
from tui.config import TuiConfig
from tui.streaming import StreamMetric


class _FakeClient:
    def network_metrics(self):
        return {
            "last_latency_ms": 14.5,
            "last_request_ts_ms": 1_700_000_000_000,
            "total_bytes_received": 1024,
            "last_error": None,
        }


class _FakeProvider:
    def __init__(self) -> None:
        self._client = _FakeClient()


class _FakeStreamManager:
    def __init__(self) -> None:
        self._messages = 10

    def metrics(self):
        self._messages += 5
        return {
            "market": StreamMetric(
                active=True,
                lag_ms=100,
                reconnect_count=1,
                error_count=0,
                messages_received=self._messages,
            )
        }

    def stream_last_seen(self):
        return {"market": 1_700_000_000_000}


def test_get_status_snapshot_uses_stream_and_alert_state(tmp_path, monkeypatch):
    config = TuiConfig(
        mode="live",
        data_root=tmp_path / "data" / "parquet",
        profile="day_trader",
        secrets_path=None,
        alerts={},
        panel_overrides={},
        config_path=tmp_path / "config.json",
    )
    app = TickerTapeApp(config)
    app.provider = _FakeProvider()
    app.stream_manager = _FakeStreamManager()
    app.alert_store.add(
        AlertEvent(
            alert_type="whale_trade",
            severity=AlertSeverity.WARNING,
            source_feed="whales",
            timestamp_ms=1_700_000_000_000,
            payload={},
        )
    )
    app.alert_store.set_muted(True)

    now_values = iter([1_700_000_000.0, 1_700_000_001.0])
    monkeypatch.setattr("tui.app.time.time", lambda: next(now_values))

    first = app.get_status_snapshot()
    second = app.get_status_snapshot()

    assert first["connection"] == "live"
    assert first["api_state"] == "ok"
    assert first["api_latency_ms"] == 14.5
    assert first["ws_live"] == 1
    assert first["ws_total"] == 1
    assert first["alert_count"] == 1
    assert first["alert_muted"] is True
    assert second["bandwidth_msg_s"] > 0.0
