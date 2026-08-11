"""Реестр и описания инструментов для модели."""

from tools.definitions import (
    ALL_TOOLS,
    SEARCH_TOOLS,
    INSTRUCTION_TOOLS,
    DETAIL_TOOLS,
    ACTION_TOOLS,
    RESOURCE_TOOLS,
)
from tools.registry import ToolRegistry

__all__ = [
    "ALL_TOOLS",
    "SEARCH_TOOLS",
    "INSTRUCTION_TOOLS",
    "DETAIL_TOOLS",
    "ACTION_TOOLS",
    "RESOURCE_TOOLS",
    "ToolRegistry",
]