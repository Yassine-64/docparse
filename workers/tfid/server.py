"""FastAPI variant for a persistent pod: POST /detect with the same payload."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from inference import DEVICE, MODEL_NAME, detect, load

app = FastAPI(title="docparse tf-id worker")


class ImageInput(BaseModel):
    image_base64: str


@app.on_event("startup")
def _warm() -> None:
    load()


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "device": DEVICE, "model": MODEL_NAME}


@app.post("/detect")
def detect_endpoint(body: ImageInput) -> dict[str, object]:
    try:
        return detect(body.image_base64)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e
