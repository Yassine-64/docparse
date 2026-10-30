"""One function per rule. A rule reads a Document and returns issues; it never mutates."""

from __future__ import annotations

from collections.abc import Callable
from statistics import median

from docparse.domain.models import BlockKind, Document
from docparse.domain.quality import QualityIssue, Severity

from .config import QualityThresholds

Rule = Callable[[Document, QualityThresholds], list[QualityIssue]]


def empty_document(doc: Document, _: QualityThresholds) -> list[QualityIssue]:
    if not doc.is_empty:
        return []
    return [
        QualityIssue(
            code="empty_document",
            severity=Severity.CRITICAL,
            message="no text or tables were extracted from any page",
        )
    ]


def scanned_pages_without_text(doc: Document, _: QualityThresholds) -> list[QualityIssue]:
    bad = [p.number for p in doc.pages if p.is_scanned and not p.text.strip()]
    if not bad:
        return []
    severity = Severity.CRITICAL if len(bad) * 2 > len(doc.pages) else Severity.WARNING
    return [
        QualityIssue(
            code="scanned_without_ocr",
            severity=severity,
            details={"pages": bad},
            message=f"{len(bad)} page(s) look scanned and have no OCR text",
        )
    ]


def low_ocr_confidence(doc: Document, t: QualityThresholds) -> list[QualityIssue]:
    issues = []
    for page in doc.pages:
        confs = [
            b.provenance.confidence for b in page.blocks if b.provenance.confidence is not None
        ]
        if confs and (mean := sum(confs) / len(confs)) < t.min_ocr_confidence:
            issues.append(
                QualityIssue(
                    code="low_ocr_confidence",
                    severity=Severity.WARNING,
                    page=page.number,
                    message=f"mean OCR confidence {mean:.2f} < {t.min_ocr_confidence}",
                )
            )
    return issues


def oversized_tables(doc: Document, t: QualityThresholds) -> list[QualityIssue]:
    return [
        QualityIssue(
            code="oversized_table",
            severity=Severity.WARNING,
            page=page.number,
            message=f"table with {b.table.cell_count} cells, likely a visualisation",
        )
        for page in doc.pages
        for b in page.blocks
        if b.kind is BlockKind.TABLE and b.table and b.table.cell_count > t.max_table_cells
    ]


def chart_like_tables(doc: Document, t: QualityThresholds) -> list[QualityIssue]:
    """Wide and mostly empty grids are Gantt/PERT charts rendered as tables: text is meaningless."""
    return [
        QualityIssue(
            code="chart_like_table",
            severity=Severity.WARNING,
            page=page.number,
            message=f"{b.table.column_count}-column table is {b.table.empty_ratio:.0%} empty",
        )
        for page in doc.pages
        for b in page.blocks
        if b.kind is BlockKind.TABLE
        and b.table
        and b.table.column_count >= t.chart_like_min_columns
        and b.table.empty_ratio >= t.chart_like_min_empty_ratio
    ]


def tiny_text(doc: Document, t: QualityThresholds) -> list[QualityIssue]:
    """Font-size proxy: very short lines relative to the page mean condensed or unreadable text."""
    issues = []
    for page in doc.pages:
        heights = [
            b.provenance.bbox.height
            for b in page.blocks
            if b.kind in (BlockKind.TEXT, BlockKind.LIST_ITEM) and b.provenance.bbox
        ]
        if len(heights) >= 3 and median(heights) < t.min_line_height_ratio:
            issues.append(
                QualityIssue(
                    code="tiny_text",
                    severity=Severity.WARNING,
                    page=page.number,
                    message=f"median text block height {median(heights):.3%} of page",
                )
            )
    return issues


DEFAULT_RULES: list[Rule] = [
    empty_document,
    scanned_pages_without_text,
    low_ocr_confidence,
    oversized_tables,
    chart_like_tables,
    tiny_text,
]
