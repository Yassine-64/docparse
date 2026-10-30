from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from PIL import Image

from docparse.domain.models import BBox, Page


@dataclass(frozen=True)
class OcrLine:
    text: str
    bbox: BBox | None
    confidence: float | None


@dataclass(frozen=True)
class OcrResult:
    lines: list[OcrLine] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines if line.text.strip())

    @property
    def mean_confidence(self) -> float | None:
        confs = [line.confidence for line in self.lines if line.confidence is not None]
        return sum(confs) / len(confs) if confs else None


@runtime_checkable
class OcrEngine(Protocol):
    """Image → lines. Used page by page when there is no usable text layer."""

    name: str

    async def recognize(self, image: Image.Image) -> OcrResult: ...


@runtime_checkable
class DocumentOcr(Protocol):
    """Whole-file OCR services (Mistral OCR style): PDF in, pages with markdown out."""

    name: str

    async def parse(self, path: Path) -> list[Page]: ...
