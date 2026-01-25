import asyncio

from backend.feeds.base import BaseFeed
from tui.streaming import StreamSupervisor


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
