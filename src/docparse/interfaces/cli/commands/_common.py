from __future__ import annotations

from docparse.infrastructure.config.logging import configure_logging
from docparse.infrastructure.config.settings import Settings
from docparse.infrastructure.di.container import Container, build_container


def container(verbose: bool = False) -> Container:
    settings = Settings()
    configure_logging("DEBUG" if verbose else settings.log_level)
    return build_container(settings)
