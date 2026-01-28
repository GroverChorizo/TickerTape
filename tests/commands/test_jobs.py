import os
import json

from commands.jobs import jobs_command
from backtesting.models import BacktestJobMetadata
from backtesting.job import write_metadata, write_result


def test_jobs_list_and_show(tmp_path):
    job_root = str(tmp_path / "jobs")
    os.makedirs(job_root, exist_ok=True)
    # create two runs
    meta1 = BacktestJobMetadata(
        run_id="run1",
        strategy="s1.py",
        strategy_version="0.1",
        dataset="ds1",
        params={"p": 1},
        seed=42,
        started_at_ms=1,
        finished_at_ms=2,
    )
    write_metadata(meta1, root=job_root)
    from backtesting.models import BacktestResult
    write_result(
        BacktestResult(run_id="run1", timestamps=[0], equity_curve=[100.0], metrics={}),
        root=job_root,
    )
    meta2 = BacktestJobMetadata(
        run_id="run2",
        strategy="s2.py",
        strategy_version="0.1",
        dataset="ds2",
        params={},
        seed=7,
        started_at_ms=10,
        finished_at_ms=20,
    )
    write_metadata(meta2, root=job_root)
    write_result(
        BacktestResult(run_id="run2", timestamps=[0, 1], equity_curve=[100.0, 101.0], metrics={}),
        root=job_root,
    )

    # list
    out = jobs_command("jobs", ["list", "--root", job_root])
    assert "run1" in out
    assert "run2" in out

    # show
    out2 = jobs_command("jobs", ["show", "run1", "--root", job_root])
    data = json.loads(out2)
    assert data["metadata"]["run_id"] == "run1"
    assert data["result_summary"]["points"] == 1

    # show missing
    out3 = jobs_command("jobs", ["show", "nope", "--root", job_root])
    assert "Run not found" in out3
