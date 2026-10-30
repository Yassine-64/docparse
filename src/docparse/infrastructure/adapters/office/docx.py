"""DOCX via python-docx, body order preserved (paragraphs and tables interleaved)."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from docx import Document as DocxFile
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph

from docparse.application.dto import ParseOptions
from docparse.domain.models import Block, BlockKind, Document, Page, Provenance, Table

SOURCE = "python-docx"
MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_HEADING = re.compile(r"heading\s*(\d)", re.I)


class DocxParser:
    suffixes = frozenset({".docx"})

    async def parse(self, path: Path, options: ParseOptions) -> Document:
        return await asyncio.to_thread(self._parse, path)

    def _parse(self, path: Path) -> Document:
        doc = DocxFile(str(path))
        section = doc.sections[0]
        page = Page(
            number=1, width=float(section.page_width or 1), height=float(section.page_height or 1)
        )
        prov = Provenance(page=1, source=SOURCE)

        for child in doc.element.body.iterchildren():
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "p":
                block = self._paragraph(Paragraph(child, doc), prov)
            elif tag == "tbl":
                block = self._table(DocxTable(child, doc), prov)
            else:
                block = None
            if block is not None:
                page.blocks.append(block)

        props = doc.core_properties
        meta = {k: v for k, v in {"title": props.title, "author": props.author}.items() if v}
        return Document(source_name=path.name, media_type=MEDIA_TYPE, pages=[page], metadata=meta)

    @staticmethod
    def _paragraph(p: Paragraph, prov: Provenance) -> Block | None:
        text = p.text.strip()
        if not text:
            return None
        style = (p.style.name if p.style is not None else "") or ""
        if style.lower() == "title":
            return Block(kind=BlockKind.HEADING, level=1, text=text, provenance=prov)
        if m := _HEADING.search(style):
            return Block(
                kind=BlockKind.HEADING, level=min(int(m.group(1)), 6), text=text, provenance=prov
            )
        if "list" in style.lower():
            return Block(kind=BlockKind.LIST_ITEM, text=text, provenance=prov)
        return Block(kind=BlockKind.TEXT, text=text, provenance=prov)

    @staticmethod
    def _table(t: DocxTable, prov: Provenance) -> Block | None:
        rows = [[c.text.strip() for c in r.cells] for r in t.rows]
        rows = [r for r in rows if any(r)]
        if not rows:
            return None
        table = Table(rows=rows)
        return Block(kind=BlockKind.TABLE, text=table.to_markdown(), table=table, provenance=prov)
