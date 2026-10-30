from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image


class PypdfiumPdf:
    """Inspector + renderer. Opens the file per call: pdfium handles are not thread safe."""

    def page_count(self, path: Path) -> int:
        doc = pdfium.PdfDocument(str(path))
        try:
            return len(doc)
        finally:
            doc.close()

    def is_encrypted(self, path: Path) -> bool:
        try:
            doc = pdfium.PdfDocument(str(path))
        except pdfium.PdfiumError as e:
            return "password" in str(e).lower()
        doc.close()
        return False

    def render(self, path: Path, page_number: int, scale: float = 2.0) -> Image.Image:
        doc = pdfium.PdfDocument(str(path))
        try:
            image: Image.Image = doc[page_number - 1].render(scale=scale).to_pil().convert("RGB")
            return image
        finally:
            doc.close()
