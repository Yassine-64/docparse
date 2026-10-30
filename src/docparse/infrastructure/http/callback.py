"""PUT the job outcome to the caller's URL, with retries. Mirrors the old CallbackService."""

from __future__ import annotations

import asyncio
import logging

import httpx

from docparse.application.jobs import Job

log = logging.getLogger(__name__)


class HttpCallbackNotifier:
    def __init__(self, attempts: int = 5, timeout: float = 30.0) -> None:
        self.attempts = attempts
        self._client = httpx.AsyncClient(timeout=timeout)

    async def notify(self, job: Job) -> None:
        assert job.callback_url
        payload = {
            "job_id": job.id,
            "status": job.status,
            "filename": job.filename,
            "error": job.error,
            "passed": job.result.report.passed if job.result else None,
        }
        delay = 1.0
        for attempt in range(1, self.attempts + 1):
            try:
                r = await self._client.put(job.callback_url, json=payload)
                r.raise_for_status()
                return
            except httpx.HTTPError as e:
                log.warning(
                    "callback attempt %d/%d for %s failed: %s", attempt, self.attempts, job.id, e
                )
                if attempt == self.attempts:
                    raise
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)
