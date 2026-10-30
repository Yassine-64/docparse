"""Composition root: Settings → adapters → use cases. The only module that imports every adapter."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from functools import cached_property

from docparse.application.engines import FallbackLayout, FallbackOcr
from docparse.application.jobs import JobService
from docparse.application.quality import QualityGate
from docparse.application.strategies import PdfStrategy, PresentationStrategy, Strategy
from docparse.application.use_cases import ChunkDocument, ExportResult, ParseDocument
from docparse.domain.ports import (
    DocumentOcr,
    LayoutDetector,
    OcrEngine,
    TextRefiner,
    VisionDescriber,
)
from docparse.infrastructure.adapters.layout.tfid import TfidLayout
from docparse.infrastructure.adapters.office.csv import CsvParser
from docparse.infrastructure.adapters.office.docx import DocxParser
from docparse.infrastructure.adapters.office.libreoffice import LibreOfficeConverter, find_soffice
from docparse.infrastructure.adapters.office.xlsx import XlsxParser
from docparse.infrastructure.adapters.pdf.plumber import PdfplumberText
from docparse.infrastructure.adapters.pdf.pypdfium import PypdfiumPdf
from docparse.infrastructure.config.settings import Settings
from docparse.infrastructure.http.callback import HttpCallbackNotifier
from docparse.infrastructure.http.transports import RunpodTransport, WorkerTransport
from docparse.infrastructure.jobs.memory import InMemoryJobStore

log = logging.getLogger(__name__)


@dataclass
class Container:
    settings: Settings

    # ---- optional engines: None when not configured -------------------------------------
    @cached_property
    def ocr(self) -> OcrEngine | None:
        """RunPod → HTTP worker → local Tesseract, each used only if the previous one fails."""
        s = self.settings
        chain: list[OcrEngine] = []
        if s.runpod_api_key and s.runpod_ocr_endpoint:
            from docparse.infrastructure.adapters.ocr.easyocr import EasyOcr

            chain.append(
                EasyOcr(
                    RunpodTransport(s.runpod_api_key, s.runpod_ocr_endpoint), name="easyocr-runpod"
                )
            )
        if s.ocr_worker_url:
            from docparse.infrastructure.adapters.ocr.easyocr import EasyOcr

            chain.append(
                EasyOcr(
                    WorkerTransport(s.ocr_worker_url.rstrip("/") + "/ocr"), name="easyocr-worker"
                )
            )
        if shutil.which(s.tesseract_cmd or "tesseract"):
            try:
                from docparse.infrastructure.adapters.ocr.tesseract import TesseractOcr

                chain.append(TesseractOcr(langs=s.tesseract_langs, cmd=s.tesseract_cmd))
            except ImportError:
                log.warning(
                    "tesseract found but pytesseract missing: pip install 'docparse[tesseract]'"
                )
        if not chain:
            return None
        return chain[0] if len(chain) == 1 else FallbackOcr(chain)

    @cached_property
    def document_ocr(self) -> DocumentOcr | None:
        if not self.settings.mistral_api_key:
            return None
        from docparse.infrastructure.adapters.ocr.mistral import MistralOcr

        return MistralOcr(self.settings.mistral_api_key, self.settings.mistral_ocr_model)

    @cached_property
    def layout(self) -> LayoutDetector | None:
        s = self.settings
        chain: list[LayoutDetector] = []
        if s.runpod_api_key and s.runpod_layout_endpoint:
            chain.append(
                TfidLayout(
                    RunpodTransport(s.runpod_api_key, s.runpod_layout_endpoint), name="tf-id-runpod"
                )
            )
        if s.layout_worker_url:
            chain.append(
                TfidLayout(
                    WorkerTransport(s.layout_worker_url.rstrip("/") + "/detect"),
                    name="tf-id-worker",
                )
            )
        if not chain:
            return None
        return chain[0] if len(chain) == 1 else FallbackLayout(chain)

    @cached_property
    def vision(self) -> VisionDescriber | None:
        if not self.settings.openai_api_key:
            return None
        from docparse.infrastructure.adapters.vision.openai import OpenAiVision

        return OpenAiVision(self.settings.openai_api_key, self.settings.openai_model)

    @cached_property
    def refiner(self) -> TextRefiner | None:
        if not self.settings.anthropic_api_key:
            return None
        from docparse.infrastructure.adapters.refiner.anthropic import AnthropicRefiner

        return AnthropicRefiner(self.settings.anthropic_api_key, self.settings.anthropic_model)

    # ---- strategies & use cases ----------------------------------------------------------
    @cached_property
    def pdf_strategy(self) -> PdfStrategy:
        pdfium = PypdfiumPdf()
        return PdfStrategy(
            inspector=pdfium,
            renderer=pdfium,
            text_extractor=PdfplumberText(),
            ocr=self.ocr,
            document_ocr=self.document_ocr,
            layout=self.layout,
            vision=self.vision,
            min_chars_per_page=self.settings.min_chars_per_page,
        )

    @cached_property
    def strategies(self) -> list[Strategy]:
        strategies: list[Strategy] = [self.pdf_strategy, DocxParser(), XlsxParser(), CsvParser()]
        if soffice := find_soffice():
            strategies.append(
                PresentationStrategy(LibreOfficeConverter(soffice), self.pdf_strategy)
            )
        return strategies

    @cached_property
    def parse_document(self) -> ParseDocument:
        return ParseDocument(self.strategies, QualityGate(self.settings.quality), self.refiner)

    @cached_property
    def chunk_document(self) -> ChunkDocument:
        return ChunkDocument()

    @cached_property
    def export_result(self) -> ExportResult:
        return ExportResult(self.chunk_document)

    @cached_property
    def job_service(self) -> JobService:
        return JobService(self.parse_document, InMemoryJobStore(), HttpCallbackNotifier())


def build_container(settings: Settings | None = None) -> Container:
    return Container(settings or Settings())
