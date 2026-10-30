from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class OcrMode(StrEnum):
    AUTO = "auto"  # OCR only pages without a usable text layer
    NEVER = "never"
    FORCE = "force"  # OCR every page even if a text layer exists


class ParseOptions(BaseModel):
    ocr: OcrMode = OcrMode.AUTO
    detect_layout: bool = Field(
        default=False, description="run the layout detector for figures/tables"
    )
    describe_figures: bool = Field(
        default=False, description="send figure crops to the vision model"
    )
    refine: bool = Field(
        default=False, description="LLM restructuring pass over the final markdown"
    )
    strict: bool = Field(default=False, description="raise QualityRejected when the gate fails")
    render_scale: float = Field(default=2.0, gt=0, le=6)
