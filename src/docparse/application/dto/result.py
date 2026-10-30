from __future__ import annotations

from pydantic import BaseModel, Field

from docparse.domain.models import Document
from docparse.domain.quality import QualityReport


class ParseResult(BaseModel):
    document: Document
    report: QualityReport
    refined_markdown: str | None = None
    timings_ms: dict[str, float] = Field(default_factory=dict)
