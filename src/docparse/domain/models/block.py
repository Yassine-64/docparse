from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .provenance import Provenance


class BlockKind(StrEnum):
    TEXT = "text"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    TABLE = "table"
    FIGURE = "figure"
    CAPTION = "caption"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"


class Table(BaseModel):
    rows: list[list[str]]
    has_header: bool = True

    @property
    def cell_count(self) -> int:
        return sum(len(r) for r in self.rows)

    @property
    def column_count(self) -> int:
        return max((len(r) for r in self.rows), default=0)

    @property
    def empty_ratio(self) -> float:
        cells = [c for r in self.rows for c in r]
        return (sum(1 for c in cells if not c.strip()) / len(cells)) if cells else 0.0

    def to_markdown(self) -> str:
        if not self.rows:
            return ""
        width = self.column_count
        rows = [[_cell(c) for c in r] + [""] * (width - len(r)) for r in self.rows]
        header, body = (rows[0], rows[1:]) if self.has_header else ([""] * width, rows)
        lines = ["| " + " | ".join(header) + " |", "|" + "---|" * width]
        lines += ["| " + " | ".join(r) + " |" for r in body]
        return "\n".join(lines)


def _cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|").strip()


class Block(BaseModel):
    kind: BlockKind
    text: str
    provenance: Provenance
    level: int | None = Field(default=None, ge=1, le=6, description="heading level")
    table: Table | None = None
    image_ref: str | None = Field(default=None, description="path or id of an extracted image")

    @property
    def is_empty(self) -> bool:
        return not self.text.strip() and self.table is None

    def to_markdown(self) -> str:
        if self.kind is BlockKind.HEADING:
            return f"{'#' * (self.level or 2)} {self.text}"
        if self.kind is BlockKind.TABLE and self.table is not None:
            return self.table.to_markdown()
        if self.kind is BlockKind.LIST_ITEM:
            return f"- {self.text}"
        if self.kind is BlockKind.FIGURE:
            ref = f"({self.image_ref})" if self.image_ref else ""
            return f"![figure]{ref}\n\n{self.text}".strip()
        return self.text
