"""Thresholds, the successor of validator_config.yaml. Override via DOCPARSE_QUALITY__<FIELD>."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QualityThresholds(BaseModel):
    min_ocr_confidence: float = Field(default=0.5, ge=0, le=1)
    max_table_cells: int = Field(
        default=200, description="above this a table is probably a visualisation"
    )
    chart_like_min_columns: int = Field(
        default=8, description="wide + sparse tables look like Gantt/PERT charts"
    )
    chart_like_min_empty_ratio: float = Field(default=0.6, ge=0, le=1)
    min_line_height_ratio: float = Field(
        default=0.006, description="median line height / page height"
    )
    max_critical: int = 0
    max_warning_page_ratio: float = Field(default=0.6, ge=0, le=1)
