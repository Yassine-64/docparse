"""Try engines in order; the first that answers wins. RunPod first, Tesseract last, for example."""

from __future__ import annotations

import dataclasses
import logging

from PIL import Image

from docparse.domain.exceptions import ExtractionFailed
from docparse.domain.ports.layout import Detection, LayoutDetector
from docparse.domain.ports.ocr import OcrEngine, OcrResult

log = logging.getLogger(__name__)


class FallbackOcr:
    """An OcrEngine made of several. The successful engine's name is stamped on the result."""

    def __init__(self, engines: list[OcrEngine]) -> None:
        if not engines:
            raise ValueError("FallbackOcr needs at least one engine")
        self.engines = engines
        self.name = " > ".join(e.name for e in engines)

    async def recognize(self, image: Image.Image) -> OcrResult:
        errors: list[str] = []
        for engine in self.engines:
            try:
                result = await engine.recognize(image)
            except Exception as e:  # noqa: BLE001 - any engine failure means "try the next one"
                log.warning(
                    "ocr engine %s failed (%s: %s); falling back", engine.name, type(e).__name__, e
                )
                errors.append(f"{engine.name}: {type(e).__name__}: {e}")
                continue
            return dataclasses.replace(result, engine=result.engine or engine.name)
        raise ExtractionFailed("all OCR engines failed: " + "; ".join(errors))


class FallbackLayout:
    """Same idea for layout detection. When every detector fails, returns no detections:
    layout is an enrichment, never a reason to fail the parse."""

    def __init__(self, detectors: list[LayoutDetector]) -> None:
        if not detectors:
            raise ValueError("FallbackLayout needs at least one detector")
        self.detectors = detectors
        self.name = " > ".join(d.name for d in detectors)

    async def detect(self, image: Image.Image) -> list[Detection]:
        for detector in self.detectors:
            try:
                return await detector.detect(image)
            except Exception as e:  # noqa: BLE001
                log.warning(
                    "layout detector %s failed (%s: %s); falling back",
                    detector.name,
                    type(e).__name__,
                    e,
                )
        log.error("all layout detectors failed; continuing without layout")
        return []
