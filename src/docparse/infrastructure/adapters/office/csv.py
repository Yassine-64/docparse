from __future__ import annotations

import asyncio
import csv
from pathlib import Path

from docparse.application.dto import ParseOptions
from docparse.domain.models import Block, BlockKind, Document, Page, Provenance, Table

SOURCE = "csv"
_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1")


def _decode(raw: bytes) -> str:
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


class CsvParser:
    suffixes = frozenset({".csv", ".tsv"})

    def __init__(self, max_rows: int = 5000) -> None:
        self.max_rows = max_rows

    async def parse(self, path: Path, options: ParseOptions) -> Document:
        return await asyncio.to_thread(self._parse, path)

    def _parse(self, path: Path) -> Document:
        text = _decode(path.read_bytes())
        try:
            dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(
                text[:4096], delimiters=",;\t|"
            )
        except csv.Error:
            dialect = csv.excel_tab if path.suffix == ".tsv" else csv.excel
        rows = [[c.strip() for c in r] for r in csv.reader(text.splitlines(), dialect)]
        rows = [r for r in rows if any(r)][: self.max_rows]
        page = Page(number=1, width=1.0, height=1.0)
        if rows:
            table = Table(rows=rows)
            page.blocks.append(
                Block(
                    kind=BlockKind.TABLE,
                    text=table.to_markdown(),
                    table=table,
                    provenance=Provenance(page=1, source=SOURCE),
                )
            )
        return Document(
            source_name=path.name,
            media_type="text/csv",
            pages=[page],
            metadata={"delimiter": dialect.delimiter, "rows": len(rows)},
        )
