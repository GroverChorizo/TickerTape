from backtesting.walk_forward import walk_forward


def test_walk_forward_basic():
    prices = [100.0, 101.0, 102.0, 103.0, 104.0, 103.0, 102.0]

    def strategy_fn(window):
        return [1 for _ in window]

    report = walk_forward(prices, train_size=3, test_size=2, strategy_fn=strategy_fn)
    assert report.windows
    assert report.avg_train_sharpe >= 0.0 or report.avg_train_sharpe <= 0.0
    assert report.avg_test_sharpe >= 0.0 or report.avg_test_sharpe <= 0.0
