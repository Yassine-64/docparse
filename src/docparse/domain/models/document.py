from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .block import Block
from .page import Page


class Document(BaseModel):
    source_name: str
    media_type: str
    pages: list[Page]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def blocks(self) -> list[Block]:
        return [b for p in self.pages for b in p.blocks]

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def is_empty(self) -> bool:
        return all(b.is_empty for b in self.blocks)

    def to_markdown(self, page_markers: bool = True) -> str:
        parts: list[str] = []
        for page in self.pages:
            if page_markers:
                parts.append(f"<!-- page {page.number} -->")
            parts.extend(b.to_markdown() for b in page.blocks if not b.is_empty)
        return "\n\n".join(parts).strip() + "\n"
