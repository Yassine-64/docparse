from __future__ import annotations

import asyncio
from collections import defaultdict

from PIL import Image

from docparse.domain.models import BBox
from docparse.domain.ports.ocr import OcrLine, OcrResult


class TesseractOcr:
    name = "tesseract"

    def __init__(self, langs: str = "eng+fra", cmd: str | None = None) -> None:
        import pytesseract

        self._pt = pytesseract
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        self.langs = langs

    async def recognize(self, image: Image.Image) -> OcrResult:
        return await asyncio.to_thread(self._recognize, image)

    def _recognize(self, image: Image.Image) -> OcrResult:
        d = self._pt.image_to_data(
            image, lang=self.langs, output_type=self._pt.Output.DICT, config="--psm 6"
        )
        w, h = image.size
        by_line: dict[tuple[int, int, int], list[int]] = defaultdict(list)
        for i, txt in enumerate(d["text"]):
            if txt.strip() and float(d["conf"][i]) >= 0:
                by_line[(d["block_num"][i], d["par_num"][i], d["line_num"][i])].append(i)
        lines = [
            OcrLine(
                text=" ".join(d["text"][i] for i in idx),
                bbox=BBox.from_absolute(
                    min(d["left"][i] for i in idx),
                    min(d["top"][i] for i in idx),
                    max(d["left"][i] + d["width"][i] for i in idx),
                    max(d["top"][i] + d["height"][i] for i in idx),
                    w,
                    h,
                ),
                confidence=sum(float(d["conf"][i]) for i in idx) / len(idx) / 100,
            )
            for idx in by_line.values()
        ]
        lines.sort(key=lambda ln: (ln.bbox.y0, ln.bbox.x0) if ln.bbox else (0, 0))
        return OcrResult(lines=lines)
