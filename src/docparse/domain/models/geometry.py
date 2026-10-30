"""Coordinates are normalized to the page: 0..1 from the top-left corner, scale independent."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


def _clamp(v: float) -> float:
    return min(1.0, max(0.0, v))


class BBox(BaseModel):
    x0: float = Field(ge=0, le=1)
    y0: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _ordered(self) -> BBox:
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError("bbox must have x0<=x1 and y0<=y1")
        return self

    @classmethod
    def from_absolute(cls, x0: float, y0: float, x1: float, y1: float, w: float, h: float) -> BBox:
        return cls(x0=_clamp(x0 / w), y0=_clamp(y0 / h), x1=_clamp(x1 / w), y1=_clamp(y1 / h))

    def to_absolute(self, w: float, h: float) -> tuple[float, float, float, float]:
        return self.x0 * w, self.y0 * h, self.x1 * w, self.y1 * h

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def union(self, other: BBox) -> BBox:
        return BBox(
            x0=min(self.x0, other.x0),
            y0=min(self.y0, other.y0),
            x1=max(self.x1, other.x1),
            y1=max(self.y1, other.y1),
        )

    def contains_center(self, other: BBox) -> bool:
        cx, cy = (other.x0 + other.x1) / 2, (other.y0 + other.y1) / 2
        return self.x0 <= cx <= self.x1 and self.y0 <= cy <= self.y1


def union_all(boxes: list[BBox]) -> BBox | None:
    if not boxes:
        return None
    out = boxes[0]
    for b in boxes[1:]:
        out = out.union(b)
    return out
