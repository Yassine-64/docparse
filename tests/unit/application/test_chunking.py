from docparse.application.use_cases import ChunkDocument
from docparse.domain.models import Block, BlockKind, Document, Page, Provenance, Table


def _doc(blocks):
    return Document(
        source_name="d.pdf",
        media_type="application/pdf",
        pages=[Page(number=1, width=1, height=1, blocks=blocks)],
    )


def _p():
    return Provenance(page=1, source="t")


def test_chunks_follow_sections_and_keep_provenance():
    doc = _doc(
        [
            Block(kind=BlockKind.HEADING, level=1, text="A", provenance=_p()),
            Block(kind=BlockKind.TEXT, text="x" * 900, provenance=_p()),
            Block(kind=BlockKind.TEXT, text="y" * 900, provenance=_p()),
            Block(kind=BlockKind.HEADING, level=2, text="A.1", provenance=_p()),
            Block(kind=BlockKind.TABLE, text="", table=Table(rows=[["h"], ["v"]]), provenance=_p()),
        ]
    )
    chunks = ChunkDocument(max_chars=1000, overlap_blocks=0)(doc)
    assert [c.section_path for c in chunks] == [["A"], ["A"], ["A", "A.1"]]
    assert chunks[0].text.startswith("# A\n\nxxx")
    assert chunks[1].text.startswith("yyy")
    assert "| h |" in chunks[2].text
    assert all(c.pages == [1] for c in chunks)


def test_overlap_repeats_trailing_block():
    doc = _doc(
        [
            Block(kind=BlockKind.TEXT, text=" ".join([f"b{i}"] * 50), provenance=_p())
            for i in range(4)
        ]
    )
    chunks = ChunkDocument(max_chars=300, overlap_blocks=1)(doc)
    assert len(chunks) >= 2
    assert chunks[0].text.split("\n\n")[-1] == chunks[1].text.split("\n\n")[0]
