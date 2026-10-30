from __future__ import annotations

from pydantic import BaseModel, Field

from .block import Block


class Page(BaseModel):
    number: int = Field(ge=1)
    width: float = Field(gt=0, description="points or pixels; only ratios matter")
    height: float = Field(gt=0)
    blocks: list[Block] = Field(default_factory=list)
    is_scanned: bool = False

    @property
    def text(self) -> str:
        return "\n".join(b.text for b in self.blocks if b.text)

    def sort_blocks(self) -> None:
        self.blocks.sort(key=lambda b: b.provenance.bbox.y0 if b.provenance.bbox else 0.0)
