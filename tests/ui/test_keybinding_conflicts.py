"""Validate that screen BINDINGS have no duplicate keys.

Checks BaseScreen and all profile/research screens for key conflicts within
each class's own BINDINGS list, and across the full MRO-inherited bindings.
"""
from __future__ import annotations

from typing import List, Tuple


def _collect_own_bindings(cls) -> List[Tuple[str, str]]:
    """Return (key, action) pairs from cls.BINDINGS (own, not inherited)."""
    own = cls.__dict__.get("BINDINGS", [])
    result = []
    for item in own:
        if isinstance(item, tuple) and len(item) >= 2:
            result.append((item[0], item[1]))
    return result


def _collect_all_bindings(cls) -> List[Tuple[str, str, str]]:
    """Return (key, action, source_class_name) for all bindings in the MRO."""
    seen_classes: set[type] = set()
    result = []
    for klass in cls.__mro__:
        if klass in seen_classes:
            continue
        seen_classes.add(klass)
        own = klass.__dict__.get("BINDINGS", [])
        for item in own:
            if isinstance(item, tuple) and len(item) >= 2:
                result.append((item[0], item[1], klass.__name__))
    return result


def _find_duplicate_keys(bindings: List[Tuple[str, str, str]]) -> List[str]:
    """Return list of keys that appear more than once."""
    from collections import Counter
    counts = Counter(key for key, _, _ in bindings)
    return [k for k, c in counts.items() if c > 1]


# ── Load screen classes ────────────────────────────────────────────────────────


def _screen_classes():
    from tui.ui.screens.base import BaseScreen
    from tui.ui.screens.profile_day_trader import DayTraderScreen
    from tui.ui.screens.profile_funding_arbitrage import FundingArbitrageScreen
    from tui.ui.screens.profile_liquidation import LiquidationHunterScreen
    from tui.ui.screens.profile_whale_watcher import WhaleWatcherScreen
    from tui.ui.screens.research import ResearchScreen

    return [
        BaseScreen,
        DayTraderScreen,
        FundingArbitrageScreen,
        LiquidationHunterScreen,
        WhaleWatcherScreen,
        ResearchScreen,
    ]


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_base_screen_has_no_duplicate_own_bindings():
    from tui.ui.screens.base import BaseScreen

    bindings = _collect_own_bindings(BaseScreen)
    keys = [k for k, _ in bindings]
    duplicates = [k for k in keys if keys.count(k) > 1]
    assert not duplicates, (
        f"BaseScreen has duplicate own bindings: {sorted(set(duplicates))}"
    )


def test_profile_screens_have_no_duplicate_own_bindings():
    screens = _screen_classes()
    conflicts = {}
    for cls in screens:
        bindings = _collect_own_bindings(cls)
        keys = [k for k, _ in bindings]
        duplicates = sorted(set(k for k in keys if keys.count(k) > 1))
        if duplicates:
            conflicts[cls.__name__] = duplicates
    assert not conflicts, (
        "Screens with duplicate own bindings: "
        + "; ".join(f"{cls}: {keys}" for cls, keys in conflicts.items())
    )


def test_no_intra_class_binding_conflicts():
    """Each screen's own BINDINGS should not override keys defined in the same list."""
    screens = _screen_classes()
    for cls in screens:
        own = _collect_own_bindings(cls)
        keys = [k for k, _ in own]
        duplicates = sorted(set(k for k in keys if keys.count(k) > 1))
        assert not duplicates, (
            f"{cls.__name__} has conflicting own bindings for keys: {duplicates}"
        )


def test_profile_screens_do_not_shadow_base_screen_bindings():
    """Profile screens must not redeclare keys already in BaseScreen.BINDINGS."""
    from tui.ui.screens.base import BaseScreen

    base_keys = {k for k, _ in _collect_own_bindings(BaseScreen)}
    screens = _screen_classes()
    shadows = {}
    for cls in screens:
        if cls is BaseScreen:
            continue
        own_keys = {k for k, _ in _collect_own_bindings(cls)}
        overlap = own_keys & base_keys
        if overlap:
            shadows[cls.__name__] = sorted(overlap)
    assert not shadows, (
        "Screens shadow BaseScreen bindings: "
        + "; ".join(f"{cls}: {keys}" for cls, keys in shadows.items())
    )
