from docparse.domain.models import BBox, BlockKind
from docparse.domain.ports.ocr import OcrLine
from docparse.domain.services import group_lines, markdown_to_blocks


def line(text, y, h=0.02, conf=0.9):
    return OcrLine(text=text, bbox=BBox(x0=0.1, y0=y, x1=0.9, y1=y + h), confidence=conf)


def test_group_lines_joins_close_lines_and_splits_on_gaps():
    blocks = group_lines(
        [line("a", 0.10), line("b", 0.125), line("c", 0.30), line("- d", 0.33)], page=1, source="t"
    )
    assert [b.text for b in blocks] == ["a b", "c", "- d"]
    assert blocks[2].kind is BlockKind.LIST_ITEM
    assert blocks[0].provenance.bbox.y1 == 0.145
    assert blocks[0].provenance.confidence == 0.9


def test_markdown_to_blocks_covers_heading_table_list_figure():
    md = (
        "# Title\n\npara one\nstill one\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        "- x\n![img](images/p1.png)\n"
    )
    blocks = markdown_to_blocks(md, page=2, source="mistral")
    kinds = [b.kind for b in blocks]
    assert kinds == [
        BlockKind.HEADING,
        BlockKind.TEXT,
        BlockKind.TABLE,
        BlockKind.LIST_ITEM,
        BlockKind.FIGURE,
    ]
    assert blocks[1].text == "para one still one"
    assert blocks[2].table.rows == [["a", "b"], ["1", "2"]]
    assert blocks[4].image_ref == "images/p1.png"
    assert all(b.provenance.page == 2 for b in blocks)
