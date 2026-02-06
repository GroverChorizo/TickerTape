from backtesting.engine import run_backtest


def test_run_backtest_basic():
    prices = [100.0, 110.0, 105.0]
    signals = [0, 1, 0]
    result = run_backtest(prices, signals, starting_cash=10_000.0)

    assert len(result.equity_curve) == len(prices)
    assert result.metrics["start"] == 10_000.0
    assert result.metrics["end"] < result.metrics["start"]
    assert "sharpe" in result.metrics
    assert result.trades
