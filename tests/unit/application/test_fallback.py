from pathlib import Path

import pytest
from PIL import Image

from docparse.application.dto import ParseOptions
from docparse.application.engines import FallbackLayout, FallbackOcr
from docparse.domain.exceptions import ExtractionFailed
from docparse.domain.models import BBox
from docparse.domain.ports.layout import Detection
from docparse.domain.ports.ocr import OcrLine, OcrResult

from .test_pdf_strategy import FakeOcr, strategy


class Broken:
    name = "runpod"

    async def recognize(self, image):
        raise ConnectionError("endpoint down")

    async def detect(self, image):
        raise ConnectionError("endpoint down")


class Working:
    name = "tesseract"

    async def recognize(self, image):
        return OcrResult(lines=[OcrLine(text="ok", bbox=None, confidence=0.7)])

    async def detect(self, image):
        return [Detection(label="figure", bbox=BBox(x0=0, y0=0, x1=0.5, y1=0.5))]


class BrokenDocOcr:
    name = "mistral"

    async def parse(self, path):
        raise TimeoutError("mistral down")


IMG = Image.new("RGB", (10, 10))


async def test_ocr_chain_uses_next_engine_and_stamps_its_name():
    chain = FallbackOcr([Broken(), Working()])
    assert chain.name == "runpod > tesseract"
    result = await chain.recognize(IMG)
    assert result.engine == "tesseract" and result.lines[0].text == "ok"


async def test_ocr_chain_raises_when_all_fail():
    with pytest.raises(ExtractionFailed, match="runpod"):
        await FallbackOcr([Broken(), Broken()]).recognize(IMG)


async def test_layout_chain_degrades_to_no_detections():
    assert len(await FallbackLayout([Broken(), Working()]).detect(IMG)) == 1
    assert await FallbackLayout([Broken()]).detect(IMG) == []


async def test_strategy_falls_back_from_document_ocr_to_per_page():
    ocr = FakeOcr()
    doc = await strategy(ocr=ocr, document_ocr=BrokenDocOcr()).parse(Path("x.pdf"), ParseOptions())
    assert ocr.calls == 1 and doc.pages[1].blocks[0].text == "ocr text"
    assert doc.metadata["engines"] == ["text-layer", "fake-ocr"]


async def test_strategy_records_engine_that_actually_answered():
    doc = await strategy(ocr=FallbackOcr([Broken(), Working()])).parse(
        Path("x.pdf"), ParseOptions()
    )
    assert doc.pages[1].blocks[0].provenance.source == "tesseract"
    assert doc.metadata["engines"] == ["text-layer", "tesseract"]


async def test_strategy_survives_layout_failure():
    doc = await strategy(layout=Broken()).parse(Path("x.pdf"), ParseOptions(detect_layout=True))
    assert doc.page_count == 2
