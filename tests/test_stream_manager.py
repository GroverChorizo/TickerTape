import time

from tui.streaming import LiveStreamManager, StreamStatus


class DummyFeed:
    def __init__(self, ts_ms=None):
        self._ts_ms = ts_ms

    def last_update_ts(self):
        return self._ts_ms


class DummyStreamer:
    def __init__(self, _provider):
        self.started = False

    def start(self, **_kwargs):
        self.started = True

    async def stop(self):
        self.started = False


class DummyProvider:
    def __init__(self, feeds):
        for name, feed in feeds.items():
            setattr(self, name, feed)


def test_stream_manager_health_and_summary():
    now_ms = int(time.time() * 1000)
    feeds = {
        "_market_feed": DummyFeed(now_ms - 500),
        "_liquidations_feed": DummyFeed(now_ms - 2500),
        "_whales_feed": DummyFeed(now_ms - 6500),
        "_funding_feed": DummyFeed(now_ms - 500),
        "_events_feed": DummyFeed(now_ms - 500),
    }
    provider = DummyProvider(feeds)
    manager = LiveStreamManager(
        provider,
        stale_after_s=1.0,
        dead_after_s=5.0,
        streamer_factory=lambda p: DummyStreamer(p),
    )
    manager.start()
    health = manager.health()
    assert health["market"].status == StreamStatus.LIVE
    assert health["liquidations"].status == StreamStatus.DEGRADED
    assert health["whales"].status == StreamStatus.OFFLINE
    summary = manager.summary()
    assert "WS:" in summary
    manager.stop()
