from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from PIL import Image

from docparse.domain.models import Page


@runtime_checkable
class PdfInspector(Protocol):
    """Cheap metadata without parsing content."""

    def page_count(self, path: Path) -> int: ...
    def is_encrypted(self, path: Path) -> bool: ...


@runtime_checkable
class PageRenderer(Protocol):
    def render(self, path: Path, page_number: int, scale: float = 2.0) -> Image.Image: ...


@runtime_checkable
class PdfTextExtractor(Protocol):
    """Reads the native text layer (and ruled tables). One Page per PDF page."""

    def extract(self, path: Path) -> list[Page]: ...
