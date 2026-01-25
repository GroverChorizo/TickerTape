import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tui.state.profiles import list_profiles, default_profile


def test_profiles_include_required():
    names = {p.name for p in list_profiles()}
    assert {"day_trader", "liquidation_hunter", "whale_watcher", "funding_arbitrage"}.issubset(names)


def test_default_profile():
    assert default_profile().name == "day_trader"
