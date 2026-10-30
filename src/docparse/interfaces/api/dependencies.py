from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from docparse.application.dto import OcrMode, ParseOptions
from docparse.infrastructure.di.container import Container

_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    c: Container = request.app.state.container
    return c


def require_api_key(
    container: Annotated[Container, Depends(get_container)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    expected = container.settings.api_key
    if expected and (credentials is None or credentials.credentials != expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or missing bearer token")


def parse_options(
    ocr: OcrMode = OcrMode.AUTO, layout: bool = False, vision: bool = False, refine: bool = False
) -> ParseOptions:
    return ParseOptions(ocr=ocr, detect_layout=layout, describe_figures=vision, refine=refine)


async def uploaded_file(
    file: UploadFile, container: Annotated[Container, Depends(get_container)]
) -> AsyncIterator[Path]:
    """Validates suffix and size, spools the upload to a temp dir that lives for the request."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in container.parse_document.supported_suffixes:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"unsupported format {suffix!r}"
        )
    data = await file.read()
    limit = container.settings.max_upload_mb
    if len(data) > limit * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"max upload is {limit} MB")
    with tempfile.TemporaryDirectory(prefix="docparse-") as tmp:
        path = Path(tmp) / Path(file.filename or "upload").name
        path.write_bytes(data)
        yield path


ContainerDep = Annotated[Container, Depends(get_container)]
OptionsDep = Annotated[ParseOptions, Depends(parse_options)]
UploadDep = Annotated[Path, Depends(uploaded_file)]
AuthDep = Depends(require_api_key)
