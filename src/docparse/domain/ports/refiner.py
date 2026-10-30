from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TextRefiner(Protocol):
    """LLM pass that restructures extracted markdown without dropping facts."""

    name: str

    async def refine(self, markdown: str) -> str: ...
