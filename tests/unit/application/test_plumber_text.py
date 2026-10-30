"""pdfplumber adapter on a stub page: SEC filings carry NUL glyphs that broke the heading marker."""

from docparse.domain.models import BlockKind
from docparse.infrastructure.adapters.pdf.plumber import PdfplumberText


def _line(text, top, size=10.0, font="Helvetica"):
    chars = [{"size": size, "fontname": font, "text": ch} for ch in text]
    return {"text": text, "x0": 10, "top": top, "x1": 300, "bottom": top + size + 2, "chars": chars}


class StubPage:
    width, height = 600.0, 800.0

    def find_tables(self):
        return []

    def extract_text_lines(self, **_):
        return [
            _line("ANNUAL REPORT", 40, size=16.0),
            _line("\x00 ANNUAL REPORT PURSUANT TO SECTION 13", 70),
            _line("Net sales were $34.2 billion.\x00", 90),
        ]


def test_nul_glyphs_are_dropped_and_headings_survive():
    page = PdfplumberText()._page(StubPage(), number=1)
    texts = [b.text for b in page.blocks]
    assert not any("\x00" in t for t in texts)
    assert page.blocks[0].kind is BlockKind.HEADING and page.blocks[0].text == "ANNUAL REPORT"
    assert "ANNUAL REPORT PURSUANT TO SECTION 13" in " ".join(texts)
    assert "Net sales were $34.2 billion." in " ".join(texts)
