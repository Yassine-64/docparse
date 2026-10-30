from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import Job


@runtime_checkable
class JobStore(Protocol):
    async def put(self, job: Job) -> None: ...
    async def get(self, job_id: str) -> Job | None: ...


@runtime_checkable
class CallbackNotifier(Protocol):
    async def notify(self, job: Job) -> None: ...
