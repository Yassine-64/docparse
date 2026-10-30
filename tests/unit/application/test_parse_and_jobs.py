from pathlib import Path

import pytest

from docparse.application.dto import ParseOptions
from docparse.application.jobs import JobService, JobStatus
from docparse.application.use_cases import ParseDocument
from docparse.domain.exceptions import QualityRejected, UnsupportedFormat
from docparse.domain.models import Block, BlockKind, Document, Page, Provenance
from docparse.infrastructure.jobs.memory import InMemoryJobStore


class EmptyStrategy:
    suffixes = frozenset({".xyz"})

    async def parse(self, path, options):
        return Document(
            source_name=path.name, media_type="x", pages=[Page(number=1, width=1, height=1)]
        )


class TextStrategy:
    suffixes = frozenset({".txt"})

    async def parse(self, path, options):
        block = Block(kind=BlockKind.TEXT, text="hello", provenance=Provenance(page=1, source="t"))
        return Document(
            source_name=path.name,
            media_type="x",
            pages=[Page(number=1, width=1, height=1, blocks=[block])],
        )


class UpperRefiner:
    name = "upper"

    async def refine(self, markdown):
        return markdown.upper()


class Recorder:
    def __init__(self):
        self.jobs = []

    async def notify(self, job):
        self.jobs.append(job)


async def test_unsupported_suffix():
    with pytest.raises(UnsupportedFormat):
        await ParseDocument([EmptyStrategy()])(Path("a.pdf"))


async def test_gate_report_and_strict():
    uc = ParseDocument([EmptyStrategy()])
    result = await uc(Path("a.xyz"))
    assert not result.report.passed and "parse" in result.timings_ms
    with pytest.raises(QualityRejected):
        await uc(Path("a.xyz"), ParseOptions(strict=True))


async def test_refiner_only_when_requested():
    uc = ParseDocument([TextStrategy()], refiner=UpperRefiner())
    assert (await uc(Path("a.txt"))).refined_markdown is None
    r = await uc(Path("a.txt"), ParseOptions(refine=True))
    assert (
        r.refined_markdown.strip().endswith("HELLO") and "upper" in r.document.metadata["engines"]
    )


async def test_job_service_records_result_failure_and_callback():
    notifier = Recorder()
    svc = JobService(ParseDocument([TextStrategy()]), InMemoryJobStore(), notifier)
    job = await svc.submit("a.txt", callback_url="http://cb")
    assert (await svc.get(job.id)).status is JobStatus.QUEUED
    await svc.run(job, Path("a.txt"), ParseOptions())
    assert job.status is JobStatus.DONE and job.result.document.blocks[0].text == "hello"
    assert notifier.jobs == [job]
    bad = await svc.submit("a.nope", None)
    await svc.run(bad, Path("a.nope"), ParseOptions())
    assert bad.status is JobStatus.FAILED and "UnsupportedFormat" in bad.error
