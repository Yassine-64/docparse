from __future__ import annotations

from pydantic import BaseModel, Field

from .issue import QualityIssue, Severity


class QualityReport(BaseModel):
    issues: list[QualityIssue] = Field(default_factory=list)
    passed: bool = True

    def count(self, severity: Severity) -> int:
        return sum(1 for i in self.issues if i.severity is severity)

    def pages_with(self, severity: Severity) -> set[int]:
        return {i.page for i in self.issues if i.severity is severity and i.page is not None}

    def to_markdown(self) -> str:
        verdict = "PASSED" if self.passed else "REJECTED"
        lines = [f"# Quality report: {verdict}", ""]
        if not self.issues:
            lines.append("No issues found.")
        for issue in self.issues:
            where = f" (page {issue.page})" if issue.page else ""
            lines.append(f"- **{issue.severity.upper()}** `{issue.code}`{where}: {issue.message}")
        return "\n".join(lines) + "\n"
