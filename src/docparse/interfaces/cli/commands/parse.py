from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from docparse.application.dto import OcrMode, ParseOptions
from docparse.domain.exceptions import DocparseError

from ._common import container


def parse(
    files: list[Path] = typer.Argument(..., exists=True, readable=True),
    out: Path = typer.Option(Path("out"), help="output directory"),
    ocr: OcrMode = typer.Option(OcrMode.AUTO),
    layout: bool = typer.Option(False, help="run the layout detector (needs a TF-ID worker)"),
    vision: bool = typer.Option(False, help="describe figures/tables with the vision model"),
    refine: bool = typer.Option(
        False, help="LLM restructuring pass (needs DOCPARSE_ANTHROPIC_API_KEY)"
    ),
    strict: bool = typer.Option(False, help="exit 2 when the quality gate rejects"),
    verbose: bool = typer.Option(False, "-v"),
) -> None:
    """Parse FILES and write .md, .json, .chunks.jsonl and .quality.md into OUT."""
    c = container(verbose)
    options = ParseOptions(
        ocr=ocr, detect_layout=layout, describe_figures=vision, refine=refine, strict=strict
    )
    failed = 0
    for path in files:
        try:
            result = asyncio.run(c.parse_document(path, options))
        except DocparseError as e:
            failed += 1
            typer.secho(f"✗ {path.name}: {e}", fg="red", err=True)
            continue
        paths = c.export_result(result, out)
        verdict = "ok" if result.report.passed else "rejected"
        typer.echo(
            f"✓ {path.name}: {result.document.page_count} page(s), "
            f"{len(result.document.blocks)} block(s), gate={verdict}, "
            f"{result.timings_ms['parse']:.0f} ms → {paths['markdown']}"
        )
    raise typer.Exit(code=2 if failed else 0)
