from __future__ import annotations

from typing import Protocol, runtime_checkable

from PIL import Image

from docparse.domain.models import Table


@runtime_checkable
class VisionDescriber(Protocol):
    """Figure/chart → text a retriever can match; table crop → Table."""

    name: str

    async def describe(self, image: Image.Image, hint: str = "") -> str: ...
    async def read_table(self, image: Image.Image) -> Table | None: ...
