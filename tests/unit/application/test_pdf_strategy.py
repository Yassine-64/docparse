"""PdfStrategy routing with fakes: no PDFs, no binaries."""

from pathlib import Path

import pytest
from PIL import Image

from docparse.application.dto import OcrMode, ParseOptions
from docparse.application.strategies import PdfStrategy
from docparse.domain.exceptions import EncryptedDocument
from docparse.domain.models import BBox, Block, BlockKind, Page, Provenance
from docparse.domain.ports.layout import Detection
from docparse.domain.ports.ocr import OcrLine, OcrResult


class FakePdf:
    def __init__(self, encrypted=False):
        self.encrypted = encrypted

    def page_count(self, path):
        return 2

    def is_encrypted(self, path):
        return self.encrypted

    def render(self, path, page_number, scale=2.0):
        return Image.new("RGB", (100, 100), "white")


class FakeText:
    def extract(self, path):
        return [
            Page(
                number=1,
                width=1,
                height=1,
                blocks=[
                    Block(
                        kind=BlockKind.TEXT,
                        text="native " * 20,
                        provenance=Provenance(page=1, source="fake"),
                    )
                ],
            ),
            Page(number=2, width=1, height=1),
        ]


class FakeOcr:
    name = "fake-ocr"

    def __init__(self):
        self.calls = 0

    async def recognize(self, image):
        self.calls += 1
        return OcrResult(
            lines=[OcrLine(text="ocr text", bbox=BBox(x0=0, y0=0, x1=1, y1=0.1), confidence=0.8)]
        )


class FakeDocOcr:
    name = "fake-doc-ocr"

    async def parse(self, path):
        return [
            Page(
                number=n,
                width=1,
                height=1,
                blocks=[
                    Block(
                        kind=BlockKind.TEXT,
                        text=f"doc-ocr {n}",
                        provenance=Provenance(page=n, source="fake-doc-ocr"),
                    )
                ],
            )
            for n in (1, 2)
        ]


class FakeLayout:
    name = "fake-layout"

    async def detect(self, image):
        return [
            Detection(label="figure", bbox=BBox(x0=0.1, y0=0.1, x1=0.5, y1=0.5), confidence=0.9)
        ]


class FakeVision:
    name = "fake-vision"

    async def describe(self, image, hint=""):
        return "a bar chart"

    async def read_table(self, image):
        return None


def strategy(**kw):
    pdf = kw.pop("pdf", FakePdf())
    return PdfStrategy(
        inspector=pdf, renderer=pdf, text_extractor=FakeText(), min_chars_per_page=20, **kw
    )


async def test_auto_mode_ocrs_only_scanned_pages():
    ocr = FakeOcr()
    doc = await strategy(ocr=ocr).parse(Path("x.pdf"), ParseOptions())
    assert ocr.calls == 1
    assert doc.pages[0].blocks[0].text.startswith("native")
    assert doc.pages[1].blocks[0].text == "ocr text"
    assert doc.pages[1].is_scanned and not doc.pages[0].is_scanned
    assert doc.metadata["engines"] == ["text-layer", "fake-ocr"]


async def test_force_mode_ocrs_every_page():
    ocr = FakeOcr()
    await strategy(ocr=ocr).parse(Path("x.pdf"), ParseOptions(ocr=OcrMode.FORCE))
    assert ocr.calls == 2


async def test_never_mode_leaves_scanned_pages_empty():
    ocr = FakeOcr()
    doc = await strategy(ocr=ocr).parse(Path("x.pdf"), ParseOptions(ocr=OcrMode.NEVER))
    assert ocr.calls == 0 and doc.pages[1].blocks == []


async def test_document_ocr_used_when_mostly_scanned():
    doc = await strategy(ocr=FakeOcr(), document_ocr=FakeDocOcr()).parse(
        Path("x.pdf"), ParseOptions()
    )
    assert [p.blocks[0].text for p in doc.pages] == ["doc-ocr 1", "doc-ocr 2"]
    assert doc.pages[1].is_scanned


async def test_layout_adds_described_figures_with_bbox():
    doc = await strategy(layout=FakeLayout(), vision=FakeVision()).parse(
        Path("x.pdf"), ParseOptions(ocr=OcrMode.NEVER, detect_layout=True, describe_figures=True)
    )
    figs = [b for b in doc.blocks if b.kind is BlockKind.FIGURE]
    assert len(figs) == 2 and figs[0].text == "a bar chart"
    assert figs[0].provenance.source == "fake-vision" and figs[0].provenance.bbox.x1 == 0.5


async def test_encrypted_raises():
    with pytest.raises(EncryptedDocument):
        await strategy(pdf=FakePdf(encrypted=True)).parse(Path("x.pdf"), ParseOptions())
