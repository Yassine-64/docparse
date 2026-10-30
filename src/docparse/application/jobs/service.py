from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from docparse.application.dto import ParseOptions
from docparse.application.use_cases import ParseDocument

from .models import Job, JobStatus
from .ports import CallbackNotifier, JobStore

log = logging.getLogger(__name__)


class JobService:
    def __init__(
        self, parser: ParseDocument, store: JobStore, notifier: CallbackNotifier | None = None
    ) -> None:
        self.parser = parser
        self.store = store
        self.notifier = notifier

    async def submit(self, filename: str, callback_url: str | None) -> Job:
        job = Job(filename=filename, callback_url=callback_url)
        await self.store.put(job)
        return job

    async def get(self, job_id: str) -> Job | None:
        return await self.store.get(job_id)

    async def run(self, job: Job, path: Path, options: ParseOptions) -> Job:
        """Runs in the background. The file at `path` is deleted by the caller afterwards."""
        job.status = JobStatus.RUNNING
        await self.store.put(job)
        try:
            job.result = await self.parser(path, options)
            job.status = JobStatus.DONE
        except Exception as e:  # noqa: BLE001 - a job must record any failure, never crash the worker
            log.exception("job %s failed", job.id)
            job.status, job.error = JobStatus.FAILED, f"{type(e).__name__}: {e}"
        job.finished_at = datetime.now(UTC)
        await self.store.put(job)
        if job.callback_url and self.notifier is not None:
            try:
                await self.notifier.notify(job)
            except Exception:  # noqa: BLE001
                log.exception("callback for job %s failed", job.id)
        return job
