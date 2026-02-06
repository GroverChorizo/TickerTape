import os

from backtesting.runner import run_from_file
from backtesting.job import read_metadata, read_result


def test_run_from_file_writes_results(tmp_path, monkeypatch):
    # copy example strategy into a temp file
    src = os.path.join(os.path.dirname(__file__), "fixtures", "example_strategy.py")
    strat = tmp_path / "example_strategy.py"
    strat.write_text(open(src).read())

    # use a temporary job root so we don't pollute user dir
    job_root = str(tmp_path / "jobs")

    result = run_from_file(
        str(strat),
        prices=[100.0, 101.0, 102.0],
        seed=42,
        job_root=job_root,
        confirm_exec=True,
    )

    assert result is not None
    assert isinstance(result.equity_curve, list)
    assert len(result.equity_curve) == 3

    # Check that run dir exists and files were written
    run_dir = os.path.join(job_root, result.run_id)
    assert os.path.isdir(run_dir)

    meta = read_metadata(run_dir)
    res = read_result(run_dir)

    assert meta["run_id"] == result.run_id
    assert res["run_id"] == result.run_id
    assert res["equity_curve"] == result.equity_curve
