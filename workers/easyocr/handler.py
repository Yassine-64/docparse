"""RunPod serverless entrypoint. Input: {"input": {"image_base64": "..."}}."""

from __future__ import annotations

import logging
from typing import Any

import runpod

from inference import recognize, reader

log = logging.getLogger("easyocr-handler")


def handler(job: dict[str, Any]) -> dict[str, Any]:
    payload = job.get("input") or {}
    image = payload.get("image_base64")
    if not image:
        return {"error": "missing input.image_base64"}
    try:
        return recognize(image)
    except Exception as e:  # noqa: BLE001 - the worker must answer, never crash
        log.exception("ocr failed")
        return {"error": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    reader()  # warm the model before taking jobs
    runpod.serverless.start({"handler": handler})
