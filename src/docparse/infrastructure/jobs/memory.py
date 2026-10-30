from __future__ import annotations

import asyncio

from docparse.application.jobs import Job


class InMemoryJobStore:
    """Single-process store. ponytail: swap for Redis/Postgres when running several replicas."""

    def __init__(self, max_jobs: int = 1000) -> None:
        self._jobs: dict[str, Job] = {}
        self._max = max_jobs
        self._lock = asyncio.Lock()

    async def put(self, job: Job) -> None:
        async with self._lock:
            self._jobs[job.id] = job
            while len(self._jobs) > self._max:
                self._jobs.pop(next(iter(self._jobs)))

    async def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)
