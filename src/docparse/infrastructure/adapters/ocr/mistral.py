"""Mistral OCR: upload the PDF, get markdown per page."""

from __future__ import annotations

import contextlib
from pathlib import Path

from docparse.domain.models import Page
from docparse.domain.services import markdown_to_blocks


class MistralOcr:
    name = "mistral-ocr"

    def __init__(self, api_key: str, model: str = "mistral-ocr-latest") -> None:
        from mistralai import Mistral

        self._client = Mistral(api_key=api_key)
        self.model = model

    async def parse(self, path: Path) -> list[Page]:
        uploaded = await self._client.files.upload_async(
            file={"file_name": path.name, "content": path.read_bytes()}, purpose="ocr"
        )
        try:
            signed = await self._client.files.get_signed_url_async(file_id=uploaded.id)
            resp = await self._client.ocr.process_async(
                model=self.model,
                document={"type": "document_url", "document_url": signed.url},
                include_image_base64=False,
            )
        finally:
            with contextlib.suppress(Exception):  # best-effort cleanup of the remote upload
                await self._client.files.delete_async(file_id=uploaded.id)
        pages = []
        for p in resp.pages:
            w, h = (
                (float(p.dimensions.width), float(p.dimensions.height))
                if p.dimensions
                else (1.0, 1.0)
            )
            number = p.index + 1
            pages.append(
                Page(
                    number=number,
                    width=w,
                    height=h,
                    blocks=markdown_to_blocks(p.markdown or "", page=number, source=self.name),
                )
            )
        return pages
