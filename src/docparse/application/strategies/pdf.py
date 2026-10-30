from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from PIL import Image

from docparse.application.dto import OcrMode, ParseOptions
from docparse.domain.exceptions import EncryptedDocument
from docparse.domain.models import Block, BlockKind, Document, Page, Provenance
from docparse.domain.ports import (
    DocumentOcr,
    LayoutDetector,
    OcrEngine,
    PageRenderer,
    PdfInspector,
    PdfTextExtractor,
    VisionDescriber,
)
from docparse.domain.services import group_lines

log = logging.getLogger(__name__)


class PdfStrategy:
    """Text layer first; OCR only where it is missing; optional layout + vision enrichment.

    1. native text via `text_extractor`; a page is `is_scanned` under `min_chars_per_page` chars.
    2. OCR needed and `document_ocr` present and most pages scanned → whole-file OCR.
    3. else per scanned page: render → `ocr` engine → paragraph blocks.
    4. optional: `layout` finds figures/tables, `vision` describes them.
    """

    suffixes = frozenset({".pdf"})

    def __init__(
        self,
        inspector: PdfInspector,
        renderer: PageRenderer,
        text_extractor: PdfTextExtractor,
        ocr: OcrEngine | None = None,
        document_ocr: DocumentOcr | None = None,
        layout: LayoutDetector | None = None,
        vision: VisionDescriber | None = None,
        min_chars_per_page: int = 50,
        max_concurrency: int = 4,
    ) -> None:
        self.inspector = inspector
        self.renderer = renderer
        self.text_extractor = text_extractor
        self.ocr = ocr
        self.document_ocr = document_ocr
        self.layout = layout
        self.vision = vision
        self.min_chars_per_page = min_chars_per_page
        self._sem = asyncio.Semaphore(max_concurrency)

    async def parse(self, path: Path, options: ParseOptions) -> Document:
        if self.inspector.is_encrypted(path):
            raise EncryptedDocument(f"{path.name} is password protected")

        pages = await asyncio.to_thread(self.text_extractor.extract, path)
        for page in pages:
            page.is_scanned = len(page.text.strip()) < self.min_chars_per_page
        scanned = [p for p in pages if p.is_scanned]
        engines = ["text-layer"]

        if self._wants_ocr(options, scanned):
            pages, engine = await self._run_ocr(path, pages, scanned, options)
            if engine:
                engines.append(engine)

        if options.detect_layout and self.layout is not None:
            await asyncio.gather(*(self._enrich_layout(path, p, options) for p in pages))
            engines.append(self.layout.name)
            if options.describe_figures and self.vision is not None:
                engines.append(self.vision.name)

        return Document(
            source_name=path.name,
            media_type="application/pdf",
            pages=pages,
            metadata={"engines": engines, "scanned_pages": [p.number for p in scanned]},
        )

    @staticmethod
    def _wants_ocr(options: ParseOptions, scanned: list[Page]) -> bool:
        return options.ocr is OcrMode.FORCE or (options.ocr is OcrMode.AUTO and bool(scanned))

    async def _run_ocr(
        self, path: Path, pages: list[Page], scanned: list[Page], options: ParseOptions
    ) -> tuple[list[Page], str | None]:
        targets = pages if options.ocr is OcrMode.FORCE else scanned
        mostly_scanned = len(targets) * 2 >= len(pages)
        if self.document_ocr is not None and mostly_scanned:
            try:
                return await self._whole_document_ocr(path, pages), self.document_ocr.name
            except Exception as e:  # noqa: BLE001 - fall back to per-page OCR
                log.warning(
                    "%s failed on %s (%s: %s); falling back to per-page OCR",
                    self.document_ocr.name,
                    path.name,
                    type(e).__name__,
                    e,
                )
        if self.ocr is not None:
            used = await asyncio.gather(*(self._ocr_page(path, p, options) for p in targets))
            return pages, " + ".join(sorted({u for u in used if u})) or self.ocr.name
        log.warning("%s: %d scanned page(s) but no OCR engine configured", path.name, len(scanned))
        return pages, None

    async def _whole_document_ocr(self, path: Path, native: list[Page]) -> list[Page]:
        assert self.document_ocr is not None
        by_number = {p.number: p for p in await self.document_ocr.parse(path)}
        merged: list[Page] = []
        for page in native:
            ocr_page = by_number.get(page.number)
            if ocr_page is not None:
                ocr_page.is_scanned = page.is_scanned
            merged.append(ocr_page or page)
        return merged

    async def _render(self, path: Path, page: Page, options: ParseOptions) -> Image.Image:
        return await asyncio.to_thread(
            self.renderer.render, path, page.number, options.render_scale
        )

    async def _ocr_page(self, path: Path, page: Page, options: ParseOptions) -> str:
        assert self.ocr is not None
        async with self._sem:
            result = await self.ocr.recognize(await self._render(path, page, options))
        engine = result.engine or self.ocr.name
        page.blocks = group_lines(result.lines, page=page.number, source=engine)
        return engine

    async def _enrich_layout(self, path: Path, page: Page, options: ParseOptions) -> None:
        assert self.layout is not None
        async with self._sem:
            image = await self._render(path, page, options)
            try:
                detections = await self.layout.detect(image)
            except Exception as e:  # noqa: BLE001 - layout is enrichment, never a reason to fail
                log.warning(
                    "layout failed on page %d (%s: %s); skipped", page.number, type(e).__name__, e
                )
                return
        for det in detections:
            if det.label == "table" and self._has_native_table_at(page, det.bbox):
                continue
            ax0, ay0, ax1, ay1 = det.bbox.to_absolute(image.width, image.height)
            crop = image.crop((int(ax0), int(ay0), int(ax1), int(ay1)))
            block = await self._block_from_detection(
                det.label, crop, page.number, det.confidence, options
            )
            if block is not None:
                block.provenance.bbox = det.bbox
                page.blocks.append(block)
        page.sort_blocks()

    @staticmethod
    def _has_native_table_at(page: Page, bbox: object) -> bool:
        from docparse.domain.models import BBox

        assert isinstance(bbox, BBox)
        return any(
            b.kind is BlockKind.TABLE
            and b.provenance.bbox is not None
            and b.provenance.bbox.contains_center(bbox)
            for b in page.blocks
        )

    async def _block_from_detection(
        self,
        label: str,
        crop: Image.Image,
        page_number: int,
        confidence: float | None,
        options: ParseOptions,
    ) -> Block | None:
        assert self.layout is not None
        prov = Provenance(page=page_number, source=self.layout.name, confidence=confidence)
        vision = self.vision if options.describe_figures else None
        if label == "table":
            if vision is None:
                return None
            table = await vision.read_table(crop)
            if table is None:
                return None
            prov.source = vision.name
            return Block(
                kind=BlockKind.TABLE, text=table.to_markdown(), table=table, provenance=prov
            )
        text = ""
        if vision is not None:
            text = await vision.describe(crop)
            prov.source = vision.name
        return Block(kind=BlockKind.FIGURE, text=text, provenance=prov)
