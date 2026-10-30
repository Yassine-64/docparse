from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field

from docparse.application.dto import ParseResult


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Job(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    filename: str
    status: JobStatus = JobStatus.QUEUED
    callback_url: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    error: str | None = None
    result: ParseResult | None = None
