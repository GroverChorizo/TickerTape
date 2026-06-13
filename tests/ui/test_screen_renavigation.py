"""Regression: re-navigating to the screen you're already on must not crash.

`_push_or_replace` used to pop the current screen and synchronously push a
fresh instance with the same fixed id (e.g. running `:moondev` while already
on MoonDev). Textual prunes the popped screen from its child registry
asynchronously, so the new id collided with the not-yet-removed one and raised
`DuplicateIds`. Re-opening the active screen should be a no-op.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("textual")

from tui.app import TickerTapeApp
from tui.config import TuiConfig


def _make_app(tmp_path: Path) -> TickerTapeApp:
    config = TuiConfig(
        mode="offline_demo",  # on_mount skips the live stream manager
        data_root=tmp_path,
        profile="day_trader",
        config_path=tmp_path / "config.json",
        secrets_path=None,
    )
    return TickerTapeApp(config)


def _moondev_count(app: TickerTapeApp) -> int:
    return sum(1 for s in app.screen_stack if getattr(s, "id", None) == "moondev")


@pytest.mark.parametrize(
    ("opener", "screen_id"),
    [
        ("_open_moondev", "moondev"),
        ("_open_ops", "ops"),
        ("_open_research", "research"),
    ],
)
def test_reopening_active_screen_does_not_crash(tmp_path, opener, screen_id):
    app = _make_app(tmp_path)

    async def _main() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            open_fn = getattr(app, opener)
            open_fn()
            await pilot.pause()
            assert getattr(app.screen, "id", None) == screen_id
            # Re-opening the screen we're already on used to raise DuplicateIds.
            open_fn()
            await pilot.pause()
            assert getattr(app.screen, "id", None) == screen_id

    asyncio.run(_main())


def test_reopen_moondev_keeps_single_instance(tmp_path):
    app = _make_app(tmp_path)

    async def _main() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            app._open_moondev()
            await pilot.pause()
            app._open_moondev()
            app._open_moondev()
            await pilot.pause()
            assert _moondev_count(app) == 1

    asyncio.run(_main())
