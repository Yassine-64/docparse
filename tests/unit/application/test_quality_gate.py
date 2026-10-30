from docparse.application.quality import QualityGate, QualityThresholds
from docparse.domain.models import Block, BlockKind, Document, Page, Provenance, Table
from docparse.domain.quality import Severity


def _doc(pages):
    return Document(source_name="d.pdf", media_type="application/pdf", pages=pages)


def _text(page, text, conf=None, bbox=None):
    return Block(
        kind=BlockKind.TEXT,
        text=text,
        provenance=Provenance(page=page, source="t", confidence=conf, bbox=bbox),
    )


def test_empty_document_is_critical():
    report = QualityGate().evaluate(_doc([Page(number=1, width=1, height=1)]))
    assert not report.passed and {i.code for i in report.issues} == {"empty_document"}


def test_scanned_without_ocr_majority_rejects():
    pages = [Page(number=i, width=1, height=1, is_scanned=True) for i in (1, 2)]
    pages.append(Page(number=3, width=1, height=1, blocks=[_text(3, "ok")]))
    report = QualityGate().evaluate(_doc(pages))
    assert not report.passed
    assert any(
        i.code == "scanned_without_ocr" and i.severity is Severity.CRITICAL for i in report.issues
    )


def test_low_confidence_is_warning_not_rejection():
    pages = [
        Page(number=1, width=1, height=1, blocks=[_text(1, "blurry", conf=0.3)]),
        Page(number=2, width=1, height=1, blocks=[_text(2, "fine", conf=0.9)]),
    ]
    report = QualityGate().evaluate(_doc(pages))
    assert report.passed and "low_ocr_confidence" in {i.code for i in report.issues}


def test_chart_like_table_and_thresholds_override():
    rows = [["t"] + [""] * 9] + [["x"] + [""] * 9 for _ in range(5)]
    page = Page(
        number=1,
        width=1,
        height=1,
        blocks=[
            Block(
                kind=BlockKind.TABLE,
                text="",
                table=Table(rows=rows),
                provenance=Provenance(page=1, source="t"),
            )
        ],
    )
    codes = {i.code for i in QualityGate().evaluate(_doc([page])).issues}
    assert "chart_like_table" in codes
    relaxed = QualityGate(QualityThresholds(chart_like_min_columns=50))
    assert "chart_like_table" not in {i.code for i in relaxed.evaluate(_doc([page])).issues}
