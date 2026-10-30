"""Markdown → blocks, for engines that answer in markdown (Mistral OCR, vision models)."""

from __future__ import annotations

import re

from docparse.domain.models import Block, BlockKind, Provenance, Table

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_IMAGE = re.compile(r"^!\[[^\]]*\]\(([^)]+)\)\s*$")
_LIST = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.*)$")
_SEPARATOR = re.compile(r":?-{2,}:?")


def parse_table(lines: list[str]) -> Table | None:
    rows = []
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells and all(_SEPARATOR.fullmatch(c) for c in cells):
            continue
        rows.append(cells)
    return Table(rows=rows) if rows else None


class _Builder:
    def __init__(self, page: int, source: str, confidence: float | None) -> None:
        self.blocks: list[Block] = []
        self._para: list[str] = []
        self._table: list[str] = []
        self._page, self._source, self._confidence = page, source, confidence

    def _prov(self) -> Provenance:
        return Provenance(page=self._page, source=self._source, confidence=self._confidence)

    def add(self, kind: BlockKind, text: str, **extra: object) -> None:
        self.flush()
        self.blocks.append(Block(kind=kind, text=text, provenance=self._prov(), **extra))  # type: ignore[arg-type]

    def para(self, line: str) -> None:
        self.flush_table()
        self._para.append(line)

    def table(self, line: str) -> None:
        self.flush_para()
        self._table.append(line)

    def flush_para(self) -> None:
        text = " ".join(s.strip() for s in self._para).strip()
        if text:
            self.blocks.append(Block(kind=BlockKind.TEXT, text=text, provenance=self._prov()))
        self._para.clear()

    def flush_table(self) -> None:
        if self._table and (t := parse_table(self._table)):
            self.blocks.append(
                Block(kind=BlockKind.TABLE, text=t.to_markdown(), table=t, provenance=self._prov())
            )
        self._table.clear()

    def flush(self) -> None:
        self.flush_para()
        self.flush_table()


def markdown_to_blocks(
    markdown: str, page: int, source: str, confidence: float | None = None
) -> list[Block]:
    b = _Builder(page, source, confidence)
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("|"):
            b.table(line)
        elif not line.strip():
            b.flush()
        elif m := _HEADING.match(line):
            b.add(BlockKind.HEADING, m.group(2).strip(), level=len(m.group(1)))
        elif m := _IMAGE.match(line):
            b.add(BlockKind.FIGURE, "", image_ref=m.group(1))
        elif m := _LIST.match(line):
            b.add(BlockKind.LIST_ITEM, m.group(1).strip())
        else:
            b.para(line)
    b.flush()
    return b.blocks
