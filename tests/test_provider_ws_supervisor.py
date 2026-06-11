import asyncio

from providers.ws import WebSocketSupervisor


class FakeAsyncIter:
    def __init__(self, seq, raise_on_enter: bool = False):
        self._seq = list(seq)
        self._idx = 0
        self._raise_on_enter = raise_on_enter

    async def __aenter__(self):
        if self._raise_on_enter:
            raise RuntimeError("connect fail")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._seq):
            raise StopAsyncIteration
        val = self._seq[self._idx]
        self._idx += 1
        await asyncio.sleep(0)  # yield control
        return val


def test_supervisor_reconnects_and_dispatches():
    async def run_test():
        seqs = [["m1", "m2"], ["m3"]]

        async def make_connect():
            if not seqs:
                raise RuntimeError("no more sequences")
            seq = seqs.pop(0)
            return FakeAsyncIter(seq)

        received = []

        async def handler(msg):
            received.append(msg)

        sup = WebSocketSupervisor(connect_factory=make_connect, min_backoff=0.01, max_backoff=0.05)
        sup.register_handler(handler)
        sup.start()
        await asyncio.sleep(0.2)
        await sup.stop()

        assert received == ["m1", "m2", "m3"]

    asyncio.run(run_test())


def test_supervisor_backoff_on_connect_error():
    async def run_test():
        calls = {"count": 0}

        async def make_connect():
            calls["count"] += 1
            if calls["count"] <= 2:
                return FakeAsyncIter([], raise_on_enter=True)
            if calls["count"] == 3:
                return FakeAsyncIter(["ok"])
            # subsequent attempts fail to avoid repeated success in test
            return FakeAsyncIter([], raise_on_enter=True)

        received = []

        async def handler(msg):
            received.append(msg)

        sup = WebSocketSupervisor(connect_factory=make_connect, min_backoff=0.01, max_backoff=0.02)
        sup.register_handler(handler)
        sup.start()
        await asyncio.sleep(0.5)
        await sup.stop()

        assert received == ["ok"]
        assert calls["count"] >= 3

    asyncio.run(run_test())


def test_supervisor_reports_structured_stats():
    async def run_test():
        calls = {"count": 0}

        async def make_connect():
            calls["count"] += 1
            if calls["count"] == 1:
                return FakeAsyncIter([], raise_on_enter=True)
            return FakeAsyncIter(["m1", "m2"])

        received = []

        async def handler(msg):
            received.append(msg)

        sup = WebSocketSupervisor(
            connect_factory=make_connect, min_backoff=0.01, max_backoff=0.02
        )
        sup.register_handler(handler)
        sup.start()
        await asyncio.sleep(0.2)
        stats = sup.stats()
        await sup.stop()

        assert received
        assert stats.connect_count >= 1
        assert stats.reconnect_count >= 1
        assert stats.messages_received >= len(received)
        assert stats.last_message_ts_ms is not None
        assert stats.last_backoff_s >= 0.0

    asyncio.run(run_test())
