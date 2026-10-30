"""FastAPI variant for a persistent pod or local GPU box: POST /ocr with the same payload."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from inference import DEVICE, LANGUAGES, recognize, reader

app = FastAPI(title="docparse easyocr worker")


class ImageInput(BaseModel):
    image_base64: str


@app.on_event("startup")
def _warm() -> None:
    reader()


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "device": DEVICE, "languages": LANGUAGES}


@app.post("/ocr")
def ocr(body: ImageInput) -> dict[str, object]:
    try:
        return recognize(body.image_base64)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e
