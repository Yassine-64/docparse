from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from PIL import Image

from docparse.domain.models import BBox


@dataclass(frozen=True)
class Detection:
    label: str  # "table" | "figure"
    bbox: BBox
    confidence: float | None = None


@runtime_checkable
class LayoutDetector(Protocol):
    name: str

    async def detect(self, image: Image.Image) -> list[Detection]: ...
