from __future__ import annotations

from docparse.domain.models import Document
from docparse.domain.quality import QualityReport, Severity

from .config import QualityThresholds
from .rules import DEFAULT_RULES, Rule


class QualityGate:
    def __init__(
        self, thresholds: QualityThresholds | None = None, rules: list[Rule] | None = None
    ) -> None:
        self.thresholds = thresholds or QualityThresholds()
        self.rules = rules if rules is not None else DEFAULT_RULES

    def evaluate(self, document: Document) -> QualityReport:
        report = QualityReport(
            issues=[i for rule in self.rules for i in rule(document, self.thresholds)]
        )
        warned = len(report.pages_with(Severity.WARNING))
        too_many_warnings = (
            bool(document.page_count)
            and warned / document.page_count > self.thresholds.max_warning_page_ratio
        )
        report.passed = (
            report.count(Severity.CRITICAL) <= self.thresholds.max_critical
            and not too_many_warnings
        )
        return report
