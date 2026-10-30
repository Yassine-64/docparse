"""EasyOCR behind workers/easyocr, reached through any Transport."""

from __future__ import annotations

from PIL import Image

from docparse.domain.models import BBox
from docparse.domain.ports.ocr import OcrLine, OcrResult
from docparse.infrastructure.http.transports import Transport, image_payload


class EasyOcr:
    name = "easyocr"

    def __init__(self, transport: Transport) -> None:
        self.transport = transport

    async def recognize(self, image: Image.Image) -> OcrResult:
        data = await self.transport.call(image_payload(image))
        if data.get("error"):
            raise RuntimeError(f"easyocr worker: {data['error']}")
        w, h = image.size
        lines = []
        for item in data.get("results", []):
            pts = item.get("bbox") or []
            bbox = None
            if pts:
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                bbox = BBox.from_absolute(min(xs), min(ys), max(xs), max(ys), w, h)
            lines.append(
                OcrLine(text=item.get("text", ""), bbox=bbox, confidence=item.get("confidence"))
            )
        lines.sort(key=lambda ln: (ln.bbox.y0, ln.bbox.x0) if ln.bbox else (0, 0))
        return OcrResult(lines=lines)
