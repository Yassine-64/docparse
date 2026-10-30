from __future__ import annotations

import base64
import io

from PIL import Image

from docparse.domain.models import Table
from docparse.domain.services import parse_table

_DESCRIBE = (
    "Describe this figure for a search index. If it is a chart, give its type, axes, legend, "
    "and the values you can read. If it contains text, transcribe it. Be literal, no commentary."
)
_TABLE = (
    "Transcribe the table in this image as a GitHub-flavored markdown table with a header row. "
    "Output only the table. If there is no table, output NONE."
)


class OpenAiVision:
    name = "openai-vision"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def describe(self, image: Image.Image, hint: str = "") -> str:
        return await self._ask(image, f"{_DESCRIBE}\nContext: {hint}" if hint else _DESCRIBE)

    async def read_table(self, image: Image.Image) -> Table | None:
        answer = await self._ask(image, _TABLE)
        if answer.strip().upper().startswith("NONE"):
            return None
        return parse_table(answer.splitlines())

    async def _ask(self, image: Image.Image, prompt: str) -> str:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        resp = await self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            max_tokens=4000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": url, "detail": "high"}},
                    ],
                }
            ],
        )
        return resp.choices[0].message.content or ""
