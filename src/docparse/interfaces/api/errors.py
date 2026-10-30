"""Domain errors → HTTP status. Routers never catch DocparseError themselves."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from docparse.domain.exceptions import (
    DocparseError,
    EncryptedDocument,
    QualityRejected,
    UnsupportedFormat,
)

_STATUS: dict[type[DocparseError], int] = {
    UnsupportedFormat: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    EncryptedDocument: status.HTTP_422_UNPROCESSABLE_ENTITY,
    QualityRejected: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DocparseError)
    async def _handle(request: Request, exc: DocparseError) -> JSONResponse:
        code = _STATUS.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
        body: dict[str, object] = {"error": type(exc).__name__, "detail": str(exc)}
        if isinstance(exc, QualityRejected):
            body["report"] = exc.report_markdown
        return JSONResponse(status_code=code, content=body)
