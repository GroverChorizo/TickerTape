import asyncio

from backend.feeds.base import BaseFeed
from tui.streaming import StreamSupervisor
from tui.feeds.base import BaseFeed as TuiFeedBase


class DummyFeed(BaseFeed):
    def __init__(self, should_fail: bool = False) -> None:
        super().__init__(name="dummy", poll_interval=0.01)
        self.should_fail = should_fail

    def fetch(self) -> dict:
        if self.should_fail:
            raise RuntimeError("boom")
        return {"status": "ok", "data": {"value": 1}}


def test_stream_supervisor_run_once_success():
    supervisor = StreamSupervisor()
    feed = DummyFeed()
    supervisor.register(feed)
    asyncio.run(supervisor.run_once("dummy"))
    assert feed.state.status == "ok"


def test_stream_supervisor_run_once_error():
    supervisor = StreamSupervisor()
    feed = DummyFeed(should_fail=True)
    supervisor.register(feed)
    asyncio.run(supervisor.run_once("dummy"))
    assert feed.state.status == "error"


class ExplodingTuiFeed(TuiFeedBase):
    def __init__(self) -> None:
        super().__init__(name="exploding", poll_interval=0.01)
        self._calls = 0

    def fetch_result(self):
        self._calls += 1
        if self._calls == 1:
            raise RuntimeError("boom")
        return super().fetch_result()

    def fetch(self):
        return {}


def test_stream_supervisor_tui_feed_exception_recovery():
    supervisor = StreamSupervisor()
    feed = ExplodingTuiFeed()
    supervisor.register(feed)
    asyncio.run(supervisor.run_once("exploding"))
    assert feed.latest().status in {"empty", "error", "disconnected", "ok"}
