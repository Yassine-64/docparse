"""Native text layer via pdfplumber: lines with bboxes, headings by font size, ruled tables."""

from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Any

import pdfplumber

from docparse.domain.models import BBox, Block, BlockKind, Page, Provenance, Table
from docparse.domain.ports.ocr import OcrLine
from docparse.domain.services import group_lines

SOURCE = "pdfplumber"
_BREAK = OcrLine(text="", bbox=None, confidence=None)
_MARK = "\x00"  # heading placeholder inside the line buffer; never present in cleaned text


def _clean(text: str) -> str:
    """PDF text layers carry NULs (checkbox glyphs in SEC filings) and other C0 controls. They are
    not text, Postgres rejects NUL in a string, and NUL is our heading marker. Drop them here."""
    return "".join(ch for ch in text if ch >= " " or ch in "\t").strip()


class PdfplumberText:
    def __init__(self, heading_ratio: float = 1.15, max_heading_chars: int = 120) -> None:
        self.heading_ratio = heading_ratio
        self.max_heading_chars = max_heading_chars

    def extract(self, path: Path) -> list[Page]:
        with pdfplumber.open(str(path)) as pdf:
            return [self._page(p, i) for i, p in enumerate(pdf.pages, start=1)]

    def _page(self, p: Any, number: int) -> Page:
        w, h = float(p.width), float(p.height)
        page = Page(number=number, width=w, height=h)
        table_boxes = self._tables(p, page, w, h)

        lines = p.extract_text_lines(layout=False, strip=True, return_chars=True)
        body_size = median([c.get("size", 0) for ln in lines for c in ln.get("chars", [])] or [0.0])

        buffered: list[OcrLine] = []
        headings: dict[int, Block] = {}
        for ln in lines:
            text = _clean(ln["text"])
            bbox = BBox.from_absolute(ln["x0"], ln["top"], ln["x1"], ln["bottom"], w, h)
            if not text or any(tb.contains_center(bbox) for tb in table_boxes):
                continue
            chars = ln.get("chars", [])
            size = median([c.get("size", 0) for c in chars] or [0.0])
            if self._is_heading(size, body_size, text) or self._is_bold_title(chars, text):
                key = len(headings)
                headings[key] = Block(
                    kind=BlockKind.HEADING,
                    text=text,
                    level=_level(size, body_size),
                    provenance=Provenance(page=number, bbox=bbox, source=SOURCE),
                )
                marker = OcrLine(text=f"{_MARK}{key}", bbox=bbox, confidence=None)
                buffered += [_BREAK, marker, _BREAK]
            else:
                buffered.append(OcrLine(text=text, bbox=bbox, confidence=None))

        for block in group_lines(buffered, page=number, source=SOURCE):
            page.blocks.append(
                headings[int(block.text[1:])] if block.text.startswith(_MARK) else block
            )
        page.sort_blocks()
        return page

    def _is_heading(self, size: float, body: float, text: str) -> bool:
        return (
            bool(body) and size >= body * self.heading_ratio and len(text) <= self.max_heading_chars
        )

    @staticmethod
    def _is_bold_title(chars: list[dict[str, Any]], text: str) -> bool:
        """Short line set entirely in a bold face, not ending a sentence: a section title."""
        if not chars or len(text) > 60 or text.endswith((".", ":", ";", ",")):
            return False
        return all(
            _is_bold_font(str(c.get("fontname", ""))) for c in chars if c.get("text", "").strip()
        )

    @staticmethod
    def _tables(p: Any, page: Page, w: float, h: float) -> list[BBox]:
        boxes: list[BBox] = []
        for t in p.find_tables():
            rows = [[_clean(c or "") for c in row] for row in t.extract()]
            rows = [r for r in rows if any(r)]
            if not rows:
                continue
            x0, y0, x1, y1 = t.bbox
            bbox = BBox.from_absolute(x0, y0, x1, y1, w, h)
            boxes.append(bbox)
            table = Table(rows=rows)
            page.blocks.append(
                Block(
                    kind=BlockKind.TABLE,
                    text=table.to_markdown(),
                    table=table,
                    provenance=Provenance(page=page.number, bbox=bbox, source=SOURCE),
                )
            )
        return boxes


_BOLD_MARKERS = ("bold", "black", "heavy", "semibold", "cmbx")  # cmbx = Computer Modern bold


def _is_bold_font(fontname: str) -> bool:
    name = fontname.lower()
    return any(m in name for m in _BOLD_MARKERS)


def _level(size: float, body: float) -> int:
    ratio = size / body if body else 1.0
    return 1 if ratio >= 1.8 else 2 if ratio >= 1.45 else 3
