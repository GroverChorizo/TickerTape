"""Deterministic tests for the Command Center analytics (pure math)."""

from __future__ import annotations

import math

from tui.analytics import (
    correlation_matrix,
    funding_extremes,
    oi_leaders,
    pct_returns,
    pearson,
    realized_vol,
    regime,
)


def test_pct_returns():
    assert pct_returns([100, 110, 99]) == [0.1, -0.1]
    assert pct_returns([]) == []
    assert pct_returns([100]) == []


def test_pearson_perfect_positive_and_negative():
    a = [1, 2, 3, 4, 5]
    assert math.isclose(pearson(a, [2, 4, 6, 8, 10]), 1.0, abs_tol=1e-9)
    assert math.isclose(pearson(a, [10, 8, 6, 4, 2]), -1.0, abs_tol=1e-9)


def test_pearson_undefined_when_flat_or_short():
    assert pearson([1, 1, 1], [1, 2, 3]) is None  # zero variance
    assert pearson([1], [1]) is None


def test_correlation_matrix_diagonal_and_symmetry():
    closes = {
        "AAA": [100, 101, 102, 103, 104],
        "BBB": [10, 10.1, 10.2, 10.3, 10.4],  # same up-drift -> highly correlated
    }
    symbols, m = correlation_matrix(closes)
    assert symbols == ["AAA", "BBB"]
    assert m[0][0] == 1.0 and m[1][1] == 1.0
    assert m[0][1] is not None and math.isclose(m[0][1], m[1][0], abs_tol=1e-9)
    assert m[0][1] > 0.9


def test_realized_vol_zero_for_constant_returns():
    assert realized_vol([0.0, 0.0, 0.0]) == 0.0
    assert realized_vol([0.01, 0.01, 0.01]) == 0.0  # constant -> no dispersion


def test_regime_trend_classification():
    up = [100 + i for i in range(40)]
    down = [100 - i for i in range(40)]
    assert regime(up)["trend"] == "up"
    assert regime(down)["trend"] == "down"
    assert regime([100, 100, 100])["trend"] in {"flat", "n/a"}


def test_funding_extremes_ordering():
    rows = [
        {"symbol": "A", "funding": 0.001},
        {"symbol": "B", "funding": -0.002},
        {"symbol": "C", "funding": 0.003},
        {"symbol": "D", "funding": None},  # ignored
    ]
    ext = funding_extremes(rows, n=2)
    assert ext["most_positive"][0] == ("C", 0.003)
    assert ext["most_negative"][0] == ("B", -0.002)


def test_oi_leaders_sorted_desc():
    rows = [
        {"symbol": "A", "open_interest": 10},
        {"symbol": "B", "open_interest": 30},
        {"symbol": "C", "open_interest": 20},
    ]
    leaders = oi_leaders(rows, n=2)
    assert [s for s, _ in leaders] == ["B", "C"]
