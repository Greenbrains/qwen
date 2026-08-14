"""
__init__.py для пакета tools.mcp

Экспортирует основные классы и функции для работы с MCP-сервером Туту.
"""

from .models import (
    MCPRequest,
    MCPError,
    MCPResponse,
    MCPTool,
    MCPToolResult,
    build_initialize_request,
    build_tools_list_request,
    build_tool_call_request,
)

from .client import AsyncMCPClient, get_settings

from .tutu_tools import (
    SEARCH_TOOLS,
    INSTRUCTION_TOOLS,
    DETAIL_TOOLS,
    ACTION_TOOLS,
    RESOURCE_TOOLS,
    ALL_TOOLS,
    TOOL_CATEGORIES,
)

__all__ = [
    # Models
    "MCPRequest",
    "MCPError", 
    "MCPResponse",
    "MCPTool",
    "MCPToolResult",
    "build_initialize_request",
    "build_tools_list_request",
    "build_tool_call_request",
    # Client
    "AsyncMCPClient",
    "get_settings",
    # Tutu tools definitions
    "SEARCH_TOOLS",
    "INSTRUCTION_TOOLS",
    "DETAIL_TOOLS",
    "ACTION_TOOLS",
    "RESOURCE_TOOLS",
    "ALL_TOOLS",
    "TOOL_CATEGORIES",
]
