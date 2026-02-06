import os

from backtesting.loader import run_strategy_file


def test_run_strategy_file(tmp_path):
    src = os.path.join(os.path.dirname(__file__), "fixtures", "example_strategy.py")
    strat = tmp_path / "example_strategy.py"
    strat.write_text(open(src).read())

    curve = run_strategy_file(
        str(strat),
        prices=[100.0, 101.0, 102.0],
        seed=123,
        confirm_exec=True,
    )
    assert isinstance(curve, list)
    assert len(curve) == 3
