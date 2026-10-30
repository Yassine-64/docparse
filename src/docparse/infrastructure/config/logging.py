from __future__ import annotations

import logging

_NOISY = ("pdfminer", "httpx", "httpcore", "PIL")


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    for name in _NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)
