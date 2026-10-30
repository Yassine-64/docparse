"""How a JSON payload reaches a model worker: a plain HTTP worker, or RunPod serverless."""

from __future__ import annotations

import asyncio
import base64
import io
from typing import Any, Protocol

import httpx
from PIL import Image


class Transport(Protocol):
    async def call(self, payload: dict[str, Any]) -> dict[str, Any]: ...


def image_payload(image: Image.Image) -> dict[str, str]:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return {"image_base64": base64.b64encode(buf.getvalue()).decode()}


class WorkerTransport:
    """POST to one of the FastAPI workers under workers/ (e.g. http://localhost:8001/ocr)."""

    def __init__(self, url: str, timeout: float = 120.0) -> None:
        self.url = url
        self._client = httpx.AsyncClient(timeout=timeout)

    async def call(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = await self._client.post(self.url, json=payload)
        r.raise_for_status()
        data: dict[str, Any] = r.json()
        return data


class RunpodTransport:
    """RunPod serverless /runsync; falls back to polling /status when the job is still queued."""

    def __init__(
        self, api_key: str, endpoint_id: str, timeout: float = 300.0, poll_s: float = 2.0
    ) -> None:
        self.base = f"https://api.runpod.ai/v2/{endpoint_id}"
        self.poll_s = poll_s
        self._client = httpx.AsyncClient(
            timeout=timeout, headers={"Authorization": f"Bearer {api_key}"}
        )

    async def call(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = await self._client.post(f"{self.base}/runsync", json={"input": payload})
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "COMPLETED":
            return dict(data.get("output", {}))
        if data.get("status") in {"IN_QUEUE", "IN_PROGRESS"} and (job := data.get("id")):
            return await self._poll(job)
        raise RuntimeError(f"runpod job failed: {data}")

    async def _poll(self, job_id: str, max_polls: int = 150) -> dict[str, Any]:
        for _ in range(max_polls):
            await asyncio.sleep(self.poll_s)
            r = await self._client.get(f"{self.base}/status/{job_id}")
            r.raise_for_status()
            data = r.json()
            if data.get("status") == "COMPLETED":
                return dict(data.get("output", {}))
            if data.get("status") == "FAILED":
                raise RuntimeError(f"runpod job {job_id} failed: {data}")
        raise TimeoutError(f"runpod job {job_id} still running after {max_polls} polls")
