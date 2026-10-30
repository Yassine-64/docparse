from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_CANDIDATES = ("soffice", "libreoffice", "/Applications/LibreOffice.app/Contents/MacOS/soffice")


def find_soffice() -> str | None:
    return next((b for b in _CANDIDATES if shutil.which(b) or Path(b).exists()), None)


class LibreOfficeConverter:
    def __init__(self, binary: str, timeout_s: int = 180) -> None:
        self.binary = binary
        self.timeout_s = timeout_s

    def to_pdf(self, path: Path, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [self.binary, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(path)],
            check=True,
            capture_output=True,
            timeout=self.timeout_s,
        )
        pdf = out_dir / f"{path.stem}.pdf"
        if not pdf.exists():
            raise RuntimeError(f"LibreOffice produced no PDF for {path.name}")
        return pdf
