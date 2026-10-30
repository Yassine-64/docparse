from __future__ import annotations

from pydantic import BaseModel

from docparse.domain.models import Chunk, Document
from docparse.domain.quality import QualityReport


class ParseResponse(BaseModel):
    document: Document
    report: QualityReport
    refined_markdown: str | None = None
    timings_ms: dict[str, float]


class MarkdownResponse(BaseModel):
    filename: str
    markdown: str
    passed: bool


class ChunksResponse(BaseModel):
    filename: str
    chunks: list[Chunk]


class Health(BaseModel):
    status: str = "ok"
    version: str
    supported: list[str]
    engines: dict[str, str | None]
