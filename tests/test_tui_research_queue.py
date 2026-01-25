import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tui.state import research


def test_research_queue_add_and_sweep(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "RESEARCH_STATE_PATH", tmp_path / "jobs.json")
    monkeypatch.setattr(research, "RESEARCH_RESULTS_DIR", tmp_path / "results")
    queue = research.ResearchQueue()

    job = queue.add_job(
        job_type="backtest",
        strategy_path="/tmp/strategy.py",
        datasets=["feed=liquidations_snapshots"],
        timeframes=["1h"],
        parameters={"alpha": "1"},
        seed=42,
    )
    assert job.status == "queued"

    jobs = queue.add_sweep(
        job_type="backtest",
        strategy_path="/tmp/strategy.py",
        datasets=["feed=liquidations_snapshots"],
        timeframes=["1h"],
        parameter_grid={"alpha": ["1", "2"], "beta": ["A"]},
        seed=7,
    )
    assert len(jobs) == 2
    assert {j.parameters["alpha"] for j in jobs} == {"1", "2"}
