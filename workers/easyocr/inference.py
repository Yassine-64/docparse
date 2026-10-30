"""EasyOCR inference shared by the RunPod handler and the FastAPI server."""

from __future__ import annotations

import base64
import os
from functools import lru_cache
from typing import Any

import easyocr
import torch

LANGUAGES = os.environ.get("OCR_LANGS", "en,fr").split(",")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=1)
def reader() -> easyocr.Reader:
    return easyocr.Reader(LANGUAGES, gpu=DEVICE == "cuda")


def recognize(image_base64: str) -> dict[str, Any]:
    """Returns {results:[{bbox:[[x,y]×4], text, confidence}], full_text}."""
    image_bytes = base64.b64decode(image_base64)
    raw = reader().readtext(image_bytes, detail=1, paragraph=False)
    results = [
        {"bbox": [[int(x), int(y)] for x, y in pts], "text": text, "confidence": float(conf)}
        for pts, text, conf in raw
    ]
    return {"results": results, "full_text": "\n".join(r["text"] for r in results)}
