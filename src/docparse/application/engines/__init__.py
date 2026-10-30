"""Policies over engines: fallback chains, retries. Pure composition of domain ports."""

from .fallback import FallbackLayout, FallbackOcr

__all__ = ["FallbackLayout", "FallbackOcr"]
