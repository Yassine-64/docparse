from __future__ import annotations

import time
from collections.abc import Iterable
from pathlib import Path

from docparse.application.dto import ParseOptions, ParseResult
from docparse.application.quality import QualityGate
from docparse.application.strategies import Strategy
from docparse.domain.exceptions import QualityRejected, UnsupportedFormat
from docparse.domain.ports import TextRefiner


class ParseDocument:
    """Pick a strategy by suffix → parse → quality gate → optional LLM refinement."""

    def __init__(
        self,
        strategies: Iterable[Strategy],
        gate: QualityGate | None = None,
        refiner: TextRefiner | None = None,
    ) -> None:
        self._by_suffix: dict[str, Strategy] = {
            suffix: s for s in strategies for suffix in s.suffixes
        }
        self.gate = gate or QualityGate()
        self.refiner = refiner

    @property
    def supported_suffixes(self) -> frozenset[str]:
        return frozenset(self._by_suffix)

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self._by_suffix

    async def __call__(self, path: Path, options: ParseOptions | None = None) -> ParseResult:
        options = options or ParseOptions()
        strategy = self._by_suffix.get(path.suffix.lower())
        if strategy is None:
            raise UnsupportedFormat(path.suffix)

        timings: dict[str, float] = {}
        t0 = time.perf_counter()
        document = await strategy.parse(path, options)
        timings["parse"] = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        report = self.gate.evaluate(document)
        timings["quality"] = (time.perf_counter() - t1) * 1000
        if options.strict and not report.passed:
            raise QualityRejected(report.to_markdown())

        refined = None
        if options.refine and self.refiner is not None:
            t2 = time.perf_counter()
            refined = await self.refiner.refine(document.to_markdown())
            timings["refine"] = (time.perf_counter() - t2) * 1000
            document.metadata.setdefault("engines", []).append(self.refiner.name)

        return ParseResult(
            document=document, report=report, refined_markdown=refined, timings_ms=timings
        )
