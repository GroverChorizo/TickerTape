from backtesting.monte_carlo import resample_paths


def test_resample_paths_deterministic():
    returns = [0.01, -0.02, 0.005]
    first = resample_paths(returns, runs=3, seed=42, starting_value=100.0)
    second = resample_paths(returns, runs=3, seed=42, starting_value=100.0)

    assert first.trajectories == second.trajectories
    assert first.percentiles["p50"] == second.percentiles["p50"]
