from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from docparse.application.jobs import JobStatus
from docparse.domain.quality import QualityReport


class JobSubmitted(BaseModel):
    job_id: str
    status: JobStatus


class JobResponse(BaseModel):
    job_id: str
    filename: str
    status: JobStatus
    created_at: datetime
    finished_at: datetime | None
    error: str | None
    report: QualityReport | None
    markdown: str | None
