from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class QualityIssue(BaseModel):
    code: str
    severity: Severity
    message: str
    page: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)
