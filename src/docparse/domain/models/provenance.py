from __future__ import annotations

from pydantic import BaseModel, Field

from .geometry import BBox


class Provenance(BaseModel):
    """Where a block came from. `source` names the engine so evals can compare engines."""

    page: int = Field(ge=1)
    bbox: BBox | None = None
    source: str
    confidence: float | None = Field(default=None, ge=0, le=1)
