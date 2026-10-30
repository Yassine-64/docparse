"""TF-ID (yifeihu/TF-ID-base, Florence-2 based) table/figure detection."""

from __future__ import annotations

import base64
import io
import logging
import os
from functools import lru_cache
from typing import Any
from unittest.mock import patch

import torch
from PIL import Image
from transformers import AutoConfig, AutoModelForCausalLM, AutoProcessor
from transformers.dynamic_module_utils import get_imports

MODEL_NAME = os.environ.get("TFID_MODEL", "yifeihu/TF-ID-base")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
PROMPT = "<OD>"
KEEP = {"table", "tabular", "figure", "chart", "plot", "diagram"}
MIN_REL_W, MIN_REL_H = 0.02, 0.015


def _imports_without_flash_attn(filename: str | os.PathLike[str]) -> list[str]:
    imports = get_imports(filename)
    if str(filename).endswith(("modeling_florence2.py", "modeling_phi.py")) and "flash_attn" in imports:
        imports.remove("flash_attn")
    return imports


@lru_cache(maxsize=1)
def load() -> tuple[Any, Any]:
    logging.getLogger("transformers.configuration_utils").setLevel(logging.CRITICAL)
    with patch("transformers.dynamic_module_utils.get_imports", _imports_without_flash_attn):
        config = AutoConfig.from_pretrained(MODEL_NAME, trust_remote_code=True)
        processor = AutoProcessor.from_pretrained(MODEL_NAME, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME, config=config, trust_remote_code=True,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
        )
    model.to(DEVICE).eval()
    return model, processor


def detect(image_base64: str) -> dict[str, Any]:
    """Returns {detections:[{bbox:[x0,y0,x1,y1] in pixels, label}]}."""
    model, processor = load()
    image = Image.open(io.BytesIO(base64.b64decode(image_base64))).convert("RGB")
    inputs = processor(text=PROMPT, images=image, return_tensors="pt")
    for key, value in inputs.items():
        if torch.is_tensor(value):
            inputs[key] = value.to(DEVICE)
    if DEVICE == "cuda":
        inputs["pixel_values"] = inputs["pixel_values"].half()
    with torch.no_grad():
        ids = model.generate(
            input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"],
            max_new_tokens=1024, do_sample=False, num_beams=3,
            pad_token_id=processor.tokenizer.pad_token_id, eos_token_id=processor.tokenizer.eos_token_id,
        )
    text = processor.batch_decode(ids, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(text, task=PROMPT, image_size=image.size).get(PROMPT, {})
    w, h = image.size
    detections = []
    for box, label in zip(parsed.get("bboxes", []), parsed.get("labels", []), strict=False):
        x0, y0, x1, y1 = (round(float(c), 2) for c in box)
        label = str(label).lower()
        if label not in KEEP or x1 <= x0 or y1 <= y0:
            continue
        if (x1 - x0) < MIN_REL_W * w or (y1 - y0) < MIN_REL_H * h:
            continue
        detections.append({"bbox": [x0, y0, x1, y1], "label": label})
    return {"detections": detections}
