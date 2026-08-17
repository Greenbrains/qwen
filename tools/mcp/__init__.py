"""MCP-подсистема агента: клиент, модели протокола, фабрика tutu-инструментов."""
from .client import SyncMCPClient
from .tutu_tools import build_tutu_tools, tutu_catalog_markdown_fallback

__all__ = ["SyncMCPClient", "build_tutu_tools", "tutu_catalog_markdown_fallback"]
