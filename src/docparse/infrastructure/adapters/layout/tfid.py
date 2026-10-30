"""TF-ID (yifeihu/TF-ID-base) table/figure detector behind workers/tfid."""

from __future__ import annotations

from PIL import Image

from docparse.domain.models import BBox
from docparse.domain.ports.layout import Detection
from docparse.infrastructure.http.transports import Transport, image_payload

_LABELS = {
    "table": "table",
    "tabular": "table",
    "figure": "figure",
    "chart": "figure",
    "plot": "figure",
    "diagram": "figure",
}


class TfidLayout:
    def __init__(
        self,
        transport: Transport,
        name: str = "tf-id",
        min_rel_w: float = 0.02,
        min_rel_h: float = 0.015,
    ) -> None:
        self.transport = transport
        self.name = name
        self.min_rel_w, self.min_rel_h = min_rel_w, min_rel_h

    async def detect(self, image: Image.Image) -> list[Detection]:
        data = await self.transport.call(image_payload(image))
        if data.get("error"):
            raise RuntimeError(f"tf-id worker: {data['error']}")
        w, h = image.size
        out: list[Detection] = []
        for obj in data.get("detections") or data.get("objects") or []:
            label = _LABELS.get(str(obj.get("label", "")).lower())
            box = [float(v) for v in obj.get("bbox") or []]
            if not label or len(box) != 4 or box[2] <= box[0] or box[3] <= box[1]:
                continue
            if (box[2] - box[0]) < self.min_rel_w * w or (box[3] - box[1]) < self.min_rel_h * h:
                continue
            x0, y0, x1, y1 = box
            out.append(
                Detection(
                    label=label,
                    bbox=BBox.from_absolute(x0, y0, x1, y1, w, h),
                    confidence=obj.get("confidence"),
                )
            )
        return out
