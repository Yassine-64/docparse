from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class OfficeConverter(Protocol):
    def to_pdf(self, path: Path, out_dir: Path) -> Path: ...
