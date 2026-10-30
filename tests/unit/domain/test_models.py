import pytest

from docparse.domain.models import BBox, Block, BlockKind, Document, Page, Provenance, Table


def test_bbox_normalizes_and_clamps():
    b = BBox.from_absolute(-5, 10, 50, 120, w=100, h=100)
    assert (b.x0, b.y0, b.x1, b.y1) == (0.0, 0.1, 0.5, 1.0)
    assert b.to_absolute(200, 200) == (0.0, 20.0, 100.0, 200.0)
    assert b.union(BBox(x0=0.6, y0=0, x1=0.7, y1=0.2)).x1 == 0.7


def test_bbox_rejects_inverted():
    with pytest.raises(ValueError):
        BBox(x0=0.5, y0=0, x1=0.2, y1=1)


def test_table_markdown_escapes_pipes_and_pads():
    t = Table(rows=[["a|b", "c"], ["1"]])
    assert t.to_markdown() == "| a\\|b | c |\n|---|---|\n| 1 |  |"
    assert t.cell_count == 3 and t.column_count == 2


def test_table_empty_ratio():
    assert Table(rows=[["a", "", ""], ["", "", "b"]]).empty_ratio == pytest.approx(4 / 6)


def test_document_markdown_has_page_markers_and_headings():
    prov = Provenance(page=1, source="t")
    doc = Document(
        source_name="x.pdf",
        media_type="application/pdf",
        pages=[
            Page(
                number=1,
                width=1,
                height=1,
                blocks=[
                    Block(kind=BlockKind.HEADING, level=1, text="Title", provenance=prov),
                    Block(kind=BlockKind.LIST_ITEM, text="item", provenance=prov),
                ],
            )
        ],
    )
    assert doc.to_markdown() == "<!-- page 1 -->\n\n# Title\n\n- item\n"
    assert not doc.is_empty
