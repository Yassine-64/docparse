"""End to end on generated files through the real container."""

import shutil

import pytest

from docparse.application.dto import ParseOptions
from docparse.domain.models import BlockKind

pytestmark = pytest.mark.integration


async def test_text_pdf_gets_heading_paragraphs_and_table(container, text_pdf, tmp_path):
    result = await container.parse_document(text_pdf)
    doc = result.document
    assert result.report.passed
    assert doc.page_count == 2 and not doc.pages[0].is_scanned
    first = doc.pages[0].blocks
    assert first[0].kind is BlockKind.HEADING and first[0].text == "Quarterly Report"
    tables = [b for b in first if b.kind is BlockKind.TABLE]
    assert tables and tables[0].table.rows[0] == ["Region", "Revenue", "Growth"]
    assert all(b.provenance.bbox is not None for b in first)
    assert tables[0].provenance.bbox.y0 > first[0].provenance.bbox.y0
    paths = container.export_result(result, tmp_path / "out")
    assert paths["markdown"].read_text().startswith("<!-- page 1 -->\n\n# Quarterly Report")
    assert container.chunk_document(doc)[0].section_path == ["Quarterly Report"]


@pytest.mark.skipif(not shutil.which("tesseract"), reason="tesseract not installed")
async def test_scanned_pdf_is_ocrd(container, scanned_pdf):
    result = await container.parse_document(scanned_pdf, ParseOptions())
    page = result.document.pages[0]
    assert page.is_scanned
    assert "INVOICE" in page.text.upper() and "1500" in page.text
    assert page.blocks[0].provenance.source == "tesseract"
    assert page.blocks[0].provenance.confidence is not None
    assert "tesseract" in result.document.metadata["engines"]


async def test_csv_docx_xlsx(container, csv_file, docx_file, xlsx_file):
    csv_doc = (await container.parse_document(csv_file)).document
    assert csv_doc.blocks[0].table.rows == [["name", "qty"], ["bolt", "10"], ["nut", "25"]]
    assert csv_doc.metadata["delimiter"] == ";"

    docx_doc = (await container.parse_document(docx_file)).document
    kinds = [b.kind for b in docx_doc.blocks]
    assert kinds == [
        BlockKind.HEADING,
        BlockKind.TEXT,
        BlockKind.HEADING,
        BlockKind.LIST_ITEM,
        BlockKind.TABLE,
    ]
    assert docx_doc.blocks[0].level == 1 and docx_doc.blocks[2].level == 2

    xlsx_doc = (await container.parse_document(xlsx_file)).document
    rows = xlsx_doc.pages[0].blocks[1].table.rows
    assert rows[0] == ["Region", "Q1", "Q2"] and rows[1] == ["EMEA", "10", "12"]
    assert rows[2] == ["merged note", "merged note", "merged note"]
