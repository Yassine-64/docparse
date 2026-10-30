from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from docparse.application.dto import ParseOptions
from docparse.domain.models import Document
from docparse.domain.ports import OfficeConverter

from .base import Strategy

_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


class PresentationStrategy:
    """PPT/PPTX → PDF (LibreOffice) → PdfStrategy. Slides keep their page numbers."""

    suffixes = frozenset({".ppt", ".pptx"})

    def __init__(self, converter: OfficeConverter, pdf: Strategy) -> None:
        self.converter = converter
        self.pdf = pdf

    async def parse(self, path: Path, options: ParseOptions) -> Document:
        with tempfile.TemporaryDirectory(prefix="docparse-pptx-") as tmp:
            pdf_path = await asyncio.to_thread(self.converter.to_pdf, path, Path(tmp))
            document = await self.pdf.parse(pdf_path, options)
        document.source_name = path.name
        document.media_type = _PPTX
        document.metadata["converted_from"] = path.suffix
        return document
