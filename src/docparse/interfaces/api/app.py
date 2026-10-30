from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from docparse import __version__
from docparse.infrastructure.config.logging import configure_logging
from docparse.infrastructure.config.settings import Settings
from docparse.infrastructure.di.container import Container, build_container

from .errors import register_error_handlers
from .routers import health, jobs, parse


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    s = settings or Settings()
    configure_logging(s.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container or build_container(s)
        yield

    app = FastAPI(title="docparse", version=__version__, lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(parse.router, prefix="/v1")
    app.include_router(jobs.router, prefix="/v1")
    return app
