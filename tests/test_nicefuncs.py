"""niceFuncs: unit-exposure backtest, metrics, permutation MC.

All price-dependent tests run on REAL bars from the repo's datadogs store
(skipped when absent) and assert mathematical invariants — no OHLCV is ever
fabricated, per hard rule #1.
"""
from __future__ import annotations

import math

import pytest

import niceFuncs


def _real_opens():
    from datadogs.config import data_dir

    if not (data_dir() / "BTC-4h.csv").exists():
        pytest.skip("no real BTC-4h.csv — run: python -m datadogs backfill BTC 4h --days 900")
    from data_loader.loader import load

    return load("BTC", "4h", quiet=True)["open"].astype(float).tolist()


def test_bars_per_year_24_7():
    assert niceFuncs.bars_per_year(4 * 3_600_000) == pytest.approx(2190.0)
    assert niceFuncs.bars_per_year(900_000) == pytest.approx(35_040.0)


def test_flat_positions_never_move_equity():
    opens = _real_opens()[:500]
    eq = niceFuncs.unit_backtest(opens, [0] * len(opens), fee_bps=6, slippage_bps=2)
    assert all(v == 1.0 for v in eq)


def test_always_long_no_cost_equals_price_ratio():
    opens = _real_opens()[:500]
    eq = niceFuncs.unit_backtest(opens, [1] * len(opens))
    # decision at bar0 close fills at opens[1]; held to the end
    assert eq[-1] == pytest.approx(opens[-1] / opens[1], rel=1e-9)


def test_entry_cost_charged_exactly_once_for_buy_and_hold():
    opens = _real_opens()[:500]
    free = niceFuncs.unit_backtest(opens, [1] * len(opens))
    paid = niceFuncs.unit_backtest(opens, [1] * len(opens), fee_bps=6, slippage_bps=2)
    assert paid[-1] == pytest.approx(free[-1] * (1 - 8 / 10_000.0), rel=1e-9)


def test_flip_costs_two_units_of_turnover():
    opens = _real_opens()[:10]
    n = len(opens)
    pos = [1] * (n // 2) + [-1] * (n - n // 2)
    free = niceFuncs.unit_backtest(opens, pos)
    paid = niceFuncs.unit_backtest(opens, pos, fee_bps=6, slippage_bps=2)
    rate = 8 / 10_000.0
    # one entry (1 unit) + one flip (2 units) = factor (1-r)^1 * (1-r)^2
    assert paid[-1] / free[-1] == pytest.approx((1 - rate) * (1 - 2 * rate), rel=1e-9)


def test_unit_backtest_no_leverage_explosion_on_persistent_short():
    # Regression for the engine pathology found 2026-06-11: a held short must
    # not compound exposure. Equity stays within sane bounds on real data.
    opens = _real_opens()
    eq = niceFuncs.unit_backtest(opens, [-1] * len(opens), fee_bps=6, slippage_bps=2)
    assert 0.0 < eq[-1] < 100.0
    assert all(v > 0 for v in eq)


def test_metrics_on_real_equity_sane():
    opens = _real_opens()
    eq = niceFuncs.unit_backtest(opens, [1] * len(opens))
    m = niceFuncs.metrics(eq, timeframe_ms=4 * 3_600_000)
    assert {"return_pct", "sharpe_ann", "sortino_ann", "max_drawdown_pct"} <= set(m)
    assert 0.0 <= m["max_drawdown_pct"] <= 100.0
    assert m["exposure_years"] == pytest.approx((len(eq) - 1) / 2190.0)


def test_permutation_mc_deterministic_and_order_invariant_final():
    opens = _real_opens()[:1000]
    eq = niceFuncs.unit_backtest(opens, [1] * len(opens))
    rets = niceFuncs.returns_from_equity(eq)
    a = niceFuncs.permutation_mc(rets, runs=50, seed=11)
    b = niceFuncs.permutation_mc(rets, runs=50, seed=11)
    assert a.dds_pct == b.dds_pct  # same seed, same permutations
    # permutation preserves the return multiset -> observed final is exact
    expected = math.prod(1 + r for r in rets)
    assert a.observed_final == pytest.approx(expected, rel=1e-9)
    assert a.max_dd_p5_pct <= a.max_dd_p50_pct <= a.max_dd_p95_pct


def test_permutation_mc_refuses_empty():
    with pytest.raises(ValueError):
        niceFuncs.permutation_mc([])
