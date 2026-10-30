"""Score docparse against ground-truth markdown.

Layout of DATA_DIR: <name>.pdf next to <name>.md (expected markdown). Prints per-file and mean
normalized edit similarity (difflib ratio on whitespace-normalized text) plus table recall
(fraction of expected table rows found verbatim). Add OHR-Bench / OmniDocBench converters here.

    uv run python evals/run_eval.py evals/data [--ocr force]
"""

from __future__ import annotations

import argparse
import asyncio
import difflib
import re
from pathlib import Path

from docparse.application.dto import OcrMode, ParseOptions
from docparse.infrastructure.config.settings import Settings
from docparse.infrastructure.di.container import build_container


def normalize(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def table_rows(md: str) -> set[str]:
    return {
        normalize(line)
        for line in md.splitlines()
        if line.strip().startswith("|") and not set(line) <= set("|-: ")
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--ocr", default="auto", choices=[m.value for m in OcrMode])
    args = ap.parse_args()

    container = build_container(Settings())
    options = ParseOptions(ocr=OcrMode(args.ocr))
    rows = []
    for pdf in sorted(args.data_dir.glob("*.pdf")):
        expected_path = pdf.with_suffix(".md")
        if not expected_path.exists():
            continue
        result = await container.parse_document(pdf, options)
        got, expected = result.document.to_markdown(), expected_path.read_text()
        sim = difflib.SequenceMatcher(None, normalize(expected), normalize(got)).ratio()
        exp_rows = table_rows(expected)
        recall = len(exp_rows & table_rows(got)) / len(exp_rows) if exp_rows else float("nan")
        rows.append((pdf.name, sim, recall, result.timings_ms["parse"]))
        ms = result.timings_ms["parse"]
        print(f"{pdf.name:40s} sim={sim:.3f} table_recall={recall:.3f} {ms:.0f}ms")
    if rows:
        sims = [r[1] for r in rows]
        recalls = [r[2] for r in rows if r[2] == r[2]]
        print(f"\nmean similarity {sum(sims) / len(sims):.3f} over {len(rows)} files", end="")
        if recalls:
            print(f", mean table recall {sum(recalls) / len(recalls):.3f}", end="")
        print()


if __name__ == "__main__":
    asyncio.run(main())
