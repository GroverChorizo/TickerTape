"""Research job orchestration for backtests, sweeps, Monte Carlo, and walk-forward runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import itertools
import json
import os
import time
import uuid


RESEARCH_STATE_PATH = Path("data/research_jobs.json")
RESEARCH_RESULTS_DIR = Path("data/research_results")


@dataclass
class ResearchJob:
    job_id: str
    job_type: str
    strategy_path: str
    datasets: List[str]
    timeframes: List[str]
    parameters: Dict[str, str]
    seed: Optional[int]
    status: str
    created_at_ms: int
    started_at_ms: Optional[int]
    completed_at_ms: Optional[int]
    result_path: Optional[str]
    error: Optional[str]

    def to_dict(self) -> Dict:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "strategy_path": self.strategy_path,
            "datasets": self.datasets,
            "timeframes": self.timeframes,
            "parameters": self.parameters,
            "seed": self.seed,
            "status": self.status,
            "created_at_ms": self.created_at_ms,
            "started_at_ms": self.started_at_ms,
            "completed_at_ms": self.completed_at_ms,
            "result_path": self.result_path,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: Dict) -> "ResearchJob":
        return cls(
            job_id=payload["job_id"],
            job_type=payload["job_type"],
            strategy_path=payload["strategy_path"],
            datasets=list(payload.get("datasets", [])),
            timeframes=list(payload.get("timeframes", [])),
            parameters=dict(payload.get("parameters", {})),
            seed=payload.get("seed"),
            status=payload.get("status", "queued"),
            created_at_ms=payload.get("created_at_ms", int(time.time() * 1000)),
            started_at_ms=payload.get("started_at_ms"),
            completed_at_ms=payload.get("completed_at_ms"),
            result_path=payload.get("result_path"),
            error=payload.get("error"),
        )


class ResearchQueue:
    def __init__(self) -> None:
        self.jobs: List[ResearchJob] = []
        self._load()

    def _ensure_paths(self) -> None:
        RESEARCH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESEARCH_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        self._ensure_paths()
        if not RESEARCH_STATE_PATH.exists():
            self.jobs = []
            return
        payload = json.loads(RESEARCH_STATE_PATH.read_text(encoding="utf-8"))
        self.jobs = [ResearchJob.from_dict(item) for item in payload.get("jobs", [])]

    def _save(self) -> None:
        self._ensure_paths()
        RESEARCH_STATE_PATH.write_text(
            json.dumps({"jobs": [job.to_dict() for job in self.jobs]}, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def add_job(
        self,
        job_type: str,
        strategy_path: str,
        datasets: List[str],
        timeframes: List[str],
        parameters: Optional[Dict[str, str]] = None,
        seed: Optional[int] = None,
    ) -> ResearchJob:
        job = ResearchJob(
            job_id=str(uuid.uuid4()),
            job_type=job_type,
            strategy_path=strategy_path,
            datasets=datasets,
            timeframes=timeframes,
            parameters=parameters or {},
            seed=seed,
            status="queued",
            created_at_ms=int(time.time() * 1000),
            started_at_ms=None,
            completed_at_ms=None,
            result_path=None,
            error=None,
        )
        self.jobs.append(job)
        self._save()
        return job

    def add_sweep(
        self,
        job_type: str,
        strategy_path: str,
        datasets: List[str],
        timeframes: List[str],
        parameter_grid: Dict[str, List[str]],
        seed: Optional[int] = None,
    ) -> List[ResearchJob]:
        keys = list(parameter_grid.keys())
        jobs: List[ResearchJob] = []
        for combo in itertools.product(*[parameter_grid[k] for k in keys]):
            params = {k: str(v) for k, v in zip(keys, combo)}
            jobs.append(
                self.add_job(
                    job_type=job_type,
                    strategy_path=strategy_path,
                    datasets=datasets,
                    timeframes=timeframes,
                    parameters=params,
                    seed=seed,
                )
            )
        return jobs

    def mark_running(self, job_id: str) -> None:
        job = self._find(job_id)
        if job:
            job.status = "running"
            job.started_at_ms = int(time.time() * 1000)
            self._save()

    def mark_complete(self, job_id: str, result_path: Optional[str] = None) -> None:
        job = self._find(job_id)
        if job:
            job.status = "completed"
            job.completed_at_ms = int(time.time() * 1000)
            job.result_path = result_path
            self._save()

    def mark_failed(self, job_id: str, error: str) -> None:
        job = self._find(job_id)
        if job:
            job.status = "failed"
            job.completed_at_ms = int(time.time() * 1000)
            job.error = error
            self._save()

    def mark_blocked(self, job_id: str, reason: str) -> None:
        job = self._find(job_id)
        if job:
            job.status = "blocked"
            job.error = reason
            self._save()

    def _find(self, job_id: str) -> Optional[ResearchJob]:
        for job in self.jobs:
            if job.job_id == job_id:
                return job
        return None

    def run_if_configured(self, job: ResearchJob) -> None:
        runner = os.environ.get("TICKERTAPE_BACKTEST_RUNNER")
        if not runner:
            self.mark_blocked(job.job_id, "No backtest runner configured (TICKERTAPE_BACKTEST_RUNNER).")
            return
        self.mark_running(job.job_id)
        result_path = str(RESEARCH_RESULTS_DIR / f"{job.job_id}.json")
        os.system(
            runner.format(
                strategy=job.strategy_path,
                dataset=job.datasets[0] if job.datasets else "",
                timeframe=job.timeframes[0] if job.timeframes else "",
                params=json.dumps(job.parameters),
                seed=job.seed or "",
                out=result_path,
            )
        )
        if Path(result_path).exists():
            self.mark_complete(job.job_id, result_path)
        else:
            self.mark_failed(job.job_id, "Runner did not produce result artifact.")
