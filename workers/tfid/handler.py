"""RunPod serverless entrypoint. Input: {"input": {"image_base64": "..."}}."""

from __future__ import annotations

import logging
from typing import Any

import runpod

from inference import detect, load

log = logging.getLogger("tfid-handler")


def handler(job: dict[str, Any]) -> dict[str, Any]:
    payload = job.get("input") or {}
    image = payload.get("image_base64")
    if not image:
        return {"error": "missing input.image_base64"}
    try:
        return detect(image)
    except Exception as e:  # noqa: BLE001
        log.exception("detection failed")
        return {"error": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    load()
    runpod.serverless.start({"handler": handler})
