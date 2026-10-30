from __future__ import annotations

from pydantic import BaseModel, Field

from .provenance import Provenance


class Chunk(BaseModel):
    """A retrieval unit. Keeps every provenance it was built from, so citations stay exact."""

    index: int
    text: str
    section_path: list[str] = Field(default_factory=list)
    provenance: list[Provenance]

    @property
    def pages(self) -> list[int]:
        return sorted({p.page for p in self.provenance})
