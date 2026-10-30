"""Async flow: POST a file → job id; poll GET /jobs/{id}; optional PUT callback when done."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from docparse.application.dto import ParseOptions
from docparse.application.jobs import Job, JobService

from ..dependencies import AuthDep, ContainerDep, OptionsDep, UploadDep
from ..schemas import JobResponse, JobSubmitted

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[AuthDep])


async def _run_and_cleanup(
    service: JobService, job: Job, path: Path, options: ParseOptions
) -> None:
    try:
        await service.run(job, path, options)
    finally:
        shutil.rmtree(path.parent, ignore_errors=True)


@router.post("", response_model=JobSubmitted, status_code=status.HTTP_202_ACCEPTED)
async def submit(
    path: UploadDep,
    options: OptionsDep,
    container: ContainerDep,
    tasks: BackgroundTasks,
    callback_url: str | None = None,
) -> JobSubmitted:
    # the request's temp dir disappears on return; keep our own copy for the background task
    keep = Path(tempfile.mkdtemp(prefix="docparse-job-")) / path.name
    shutil.copyfile(path, keep)
    job = await container.job_service.submit(path.name, callback_url)
    tasks.add_task(_run_and_cleanup, container.job_service, job, keep, options)
    return JobSubmitted(job_id=job.id, status=job.status)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, container: ContainerDep) -> JobResponse:
    job = await container.job_service.get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown job")
    r = job.result
    return JobResponse(
        job_id=job.id,
        filename=job.filename,
        status=job.status,
        created_at=job.created_at,
        finished_at=job.finished_at,
        error=job.error,
        report=r.report if r else None,
        markdown=(r.refined_markdown or r.document.to_markdown()) if r else None,
    )
