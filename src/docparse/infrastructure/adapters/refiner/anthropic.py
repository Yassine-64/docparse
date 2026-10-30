"""The old 'premium' mode: an LLM rewrites the extracted markdown into a clean document.

Rules carried over from the original prompt: keep every number, reference, contact and unit;
drop page markers and extraction artefacts; merge by topic; proper headings, lists and tables.
"""

from __future__ import annotations

_SYSTEM = """You restructure extracted document text into clean, professional Markdown.

Absolute rules:
1. Exhaustive: never drop information. Keep every number, date, reference, code, contact,
   price, dimension and unit. Keep every figure description.
2. Clean: remove page markers, '====' rulers, '[OCR]'-style artefacts and stray page numbers.
   Merge content by topic, not by page. Repair sentences broken across lines.
3. Structure: '#'/'##'/'###' headings, bullet and numbered lists, **bold** for key points,
   GitHub-flavored tables with a header row.
4. Output only the restructured Markdown. No preamble, no commentary."""


class AnthropicRefiner:
    name = "anthropic-refiner"

    def __init__(
        self, api_key: str, model: str = "claude-sonnet-5-5", max_tokens: int = 16000
    ) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    async def refine(self, markdown: str) -> str:
        msg = await self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=_SYSTEM,
            messages=[{"role": "user", "content": markdown}],
        )
        return "".join(getattr(block, "text", "") for block in msg.content)
