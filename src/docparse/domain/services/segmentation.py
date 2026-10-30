"""Turn OCR / text-layer lines into paragraph blocks."""

from __future__ import annotations

from docparse.domain.models import Block, BlockKind, Provenance
from docparse.domain.models.geometry import union_all
from docparse.domain.ports.ocr import OcrLine

_BULLETS = ("-", "•", "·", "◦", "▪", "*", "–")


def is_list_item(text: str) -> bool:
    t = text.lstrip()
    if t.startswith(_BULLETS):
        return True
    head = t.split(" ", 1)[0].rstrip(".)")
    return head.isdigit() and len(head) <= 3 and " " in t


def group_lines(
    lines: list[OcrLine], page: int, source: str, gap_factor: float = 0.6
) -> list[Block]:
    """Consecutive lines whose vertical gap is small join one paragraph.

    gap_factor is relative to the median line height. An empty line forces a paragraph break.
    """
    blocks: list[Block] = []
    current: list[OcrLine] = []
    heights = [ln.bbox.height for ln in lines if ln.bbox]
    median_h = sorted(heights)[len(heights) // 2] if heights else 0.0

    def flush() -> None:
        if not current:
            return
        text = " ".join(ln.text.strip() for ln in current if ln.text.strip())
        if text:
            confs = [ln.confidence for ln in current if ln.confidence is not None]
            kind = (
                BlockKind.LIST_ITEM if len(current) == 1 and is_list_item(text) else BlockKind.TEXT
            )
            blocks.append(
                Block(
                    kind=kind,
                    text=text,
                    provenance=Provenance(
                        page=page,
                        bbox=union_all([ln.bbox for ln in current if ln.bbox]),
                        source=source,
                        confidence=sum(confs) / len(confs) if confs else None,
                    ),
                )
            )
        current.clear()

    prev: OcrLine | None = None
    for line in lines:
        if not line.text.strip():
            flush()
            prev = None
            continue
        if prev is not None:
            if prev.bbox and line.bbox:
                gap = line.bbox.y0 - prev.bbox.y1
                if is_list_item(line.text) or gap > gap_factor * median_h:
                    flush()
            else:
                flush()
        current.append(line)
        prev = line
    flush()
    return blocks
