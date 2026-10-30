from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from docparse.application.use_cases import ChunkDocument

from ._common import container


def chunks(file: Path = typer.Argument(..., exists=True), max_chars: int = 1500) -> None:
    """Print retrieval chunks for FILE as JSON lines."""
    c = container()
    result = asyncio.run(c.parse_document(file))
    for chunk in ChunkDocument(max_chars=max_chars)(result.document):
        typer.echo(json.dumps(chunk.model_dump(), ensure_ascii=False))
