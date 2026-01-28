"""Example deterministic strategy for tests."""

__version__ = "0.1"


def run(prices, seed=None):
    """Return a simple equity curve equal to cumulative returns from prices."""
    equity = []
    start = 100.0
    eq = start
    for p in prices:
        # naive: increase equity proportional to price increments
        eq = eq + (p - prices[0]) * 0.01
        equity.append(eq)
    return equity
