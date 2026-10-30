from __future__ import annotations

from fastapi import APIRouter

from docparse.application.use_cases import ChunkDocument

from ..dependencies import AuthDep, ContainerDep, OptionsDep, UploadDep
from ..schemas import ChunksResponse, MarkdownResponse, ParseResponse

router = APIRouter(prefix="/parse", tags=["parse"], dependencies=[AuthDep])


@router.post("", response_model=ParseResponse, summary="Full structured result")
async def parse(path: UploadDep, options: OptionsDep, container: ContainerDep) -> ParseResponse:
    r = await container.parse_document(path, options)
    return ParseResponse(
        document=r.document,
        report=r.report,
        refined_markdown=r.refined_markdown,
        timings_ms=r.timings_ms,
    )


@router.post("/markdown", response_model=MarkdownResponse, summary="Markdown only")
async def parse_markdown(
    path: UploadDep, options: OptionsDep, container: ContainerDep
) -> MarkdownResponse:
    r = await container.parse_document(path, options)
    return MarkdownResponse(
        filename=path.name,
        markdown=r.refined_markdown or r.document.to_markdown(),
        passed=r.report.passed,
    )


@router.post("/chunks", response_model=ChunksResponse, summary="RAG chunks with provenance")
async def parse_chunks(
    path: UploadDep, options: OptionsDep, container: ContainerDep, max_chars: int = 1500
) -> ChunksResponse:
    r = await container.parse_document(path, options)
    return ChunksResponse(filename=path.name, chunks=ChunkDocument(max_chars=max_chars)(r.document))
