from __future__ import annotations

from fastapi import APIRouter

from docparse import __version__

from ..dependencies import ContainerDep
from ..schemas import Health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health)
async def health(container: ContainerDep) -> Health:
    engines = {
        "ocr": container.ocr.name if container.ocr else None,
        "document_ocr": container.document_ocr.name if container.document_ocr else None,
        "layout": container.layout.name if container.layout else None,
        "vision": container.vision.name if container.vision else None,
        "refiner": container.refiner.name if container.refiner else None,
    }
    return Health(
        version=__version__,
        supported=sorted(container.parse_document.supported_suffixes),
        engines=engines,
    )
