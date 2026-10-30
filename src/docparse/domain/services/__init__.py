"""Pure domain services: functions over models, no I/O."""

from .markdown import markdown_to_blocks, parse_table
from .segmentation import group_lines

__all__ = ["group_lines", "markdown_to_blocks", "parse_table"]
