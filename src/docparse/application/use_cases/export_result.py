from __future__ import annotations

import json
from pathlib import Path

from docparse.application.dto import ParseResult

from .chunk_document import ChunkDocument


class ExportResult:
    """Writes <stem>.md, .json, .chunks.jsonl, .quality.md (+ .refined.md when present)."""

    def __init__(self, chunker: ChunkDocument | None = None) -> None:
        self.chunker = chunker or ChunkDocument()

    def __call__(
        self, result: ParseResult, out_dir: Path, stem: str | None = None
    ) -> dict[str, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = stem or Path(result.document.source_name).stem
        paths = {
            "markdown": out_dir / f"{stem}.md",
            "json": out_dir / f"{stem}.json",
            "chunks": out_dir / f"{stem}.chunks.jsonl",
            "quality": out_dir / f"{stem}.quality.md",
        }
        paths["markdown"].write_text(result.document.to_markdown(), encoding="utf-8")
        paths["json"].write_text(result.model_dump_json(indent=2), encoding="utf-8")
        with paths["chunks"].open("w", encoding="utf-8") as fh:
            for chunk in self.chunker(result.document):
                fh.write(json.dumps(chunk.model_dump(), ensure_ascii=False) + "\n")
        paths["quality"].write_text(result.report.to_markdown(), encoding="utf-8")
        if result.refined_markdown is not None:
            paths["refined"] = out_dir / f"{stem}.refined.md"
            paths["refined"].write_text(result.refined_markdown, encoding="utf-8")
        return paths
