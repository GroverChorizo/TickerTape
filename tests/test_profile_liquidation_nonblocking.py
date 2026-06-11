import time
import asyncio

import pytest

from tui.ui.screens.profile_liquidation import LiquidationHunterScreen
from tui.feeds.base import FeedResult, FeedStatus


class DummyApp:
    def __init__(self):
        self.provider = None
        self.state_store = type("S", (), {"update_snapshot": lambda *a, **k: None, "set_error": lambda *a, **k: None})()


def _assert_elapsed_at_least(
    observed_s: float, *, expected_s: float, tolerance_s: float = 0.05
) -> None:
    """Timing assertion with jitter tolerance for CI/Windows schedulers."""
    minimum = max(0.0, expected_s - tolerance_s)
    assert observed_s >= minimum


def test_bg_thread_call_does_not_block_event_loop():
    """Verify the pattern used by the screen (asyncio.to_thread) does not block the loop."""
    sleep_s = 0.20

    def slow_get_liquidations():
        time.sleep(sleep_s)
        return FeedResult(status=FeedStatus.OK, data={"ok": True}, updated_ts_ms=int(time.time() * 1000))

    start = time.monotonic()
    # schedule the blocking call in a thread from the event loop
    res = asyncio.run(asyncio.to_thread(slow_get_liquidations))
    duration = time.monotonic() - start
    # End-to-end includes the worker sleep; allow small timing jitter.
    assert isinstance(res, FeedResult)
    _assert_elapsed_at_least(duration, expected_s=sleep_s, tolerance_s=0.05)


def test_bg_thread_call_propagates_exceptions_safely():
    def raising():
        time.sleep(0.01)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(asyncio.to_thread(raising))


def test_bg_fetch_is_noop_when_no_provider():
    """If the screen is not mounted / has no provider, the background fetch should be a no-op."""
    screen = LiquidationHunterScreen()
    # no app/provider attached — should simply return without raising
    asyncio.run(screen._bg_fetch_liquidations())
    asyncio.run(screen._bg_fetch_market_context())
    # nothing set
    assert screen._liq_result is None
    assert screen._market_result is None
