from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from docparse.application.dto import ParseOptions
from docparse.domain.models import Document


@runtime_checkable
class Strategy(Protocol):
    """One per family of formats. Office parsers in infrastructure/ satisfy this directly."""

    suffixes: frozenset[str]

    async def parse(self, path: Path, options: ParseOptions) -> Document: ...
