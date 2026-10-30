"""Ports: what the application needs from the outside world. One file per capability."""

from .layout import Detection, LayoutDetector
from .ocr import DocumentOcr, OcrEngine, OcrLine, OcrResult
from .office import OfficeConverter
from .pdf import PageRenderer, PdfInspector, PdfTextExtractor
from .refiner import TextRefiner
from .vision import VisionDescriber

__all__ = [
    "Detection",
    "DocumentOcr",
    "LayoutDetector",
    "OcrEngine",
    "OcrLine",
    "OcrResult",
    "OfficeConverter",
    "PageRenderer",
    "PdfInspector",
    "PdfTextExtractor",
    "TextRefiner",
    "VisionDescriber",
]
