"""
Pydantic-модели для JSON-RPC 2.0 и MCP-протокола.

Используются обоими клиентами (sync/async) для валидации запросов и ответов.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MCPRequest(BaseModel):
    """Запрос JSON-RPC 2.0."""
    jsonrpc: str = "2.0"
    id: str
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)


class MCPError(BaseModel):
    """Ошибка JSON-RPC 2.0."""
    code: int
    message: str
    data: Optional[Any] = None


class MCPResponse(BaseModel):
    """Ответ JSON-RPC 2.0."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[MCPError] = None


class MCPTool(BaseModel):
    """Описание инструмента MCP (из tools/list)."""
    name: str
    description: Optional[str] = None
    inputSchema: Optional[Dict[str, Any]] = None


class MCPToolResult(BaseModel):
    """Результат вызова инструмента (tools/call)."""
    content: List[Dict[str, Any]] = Field(default_factory=list)
    isError: bool = False
    structuredContent: Optional[Any] = None


def build_initialize_request(
    request_id: str,
    protocol_version: str,
    client_name: str,
    client_version: str,
) -> MCPRequest:
    """Собирает payload для метода initialize."""
    return MCPRequest(
        id=request_id,
        method="initialize",
        params={
            "protocolVersion": protocol_version,
            "capabilities": {},
            "clientInfo": {"name": client_name, "version": client_version},
        },
    )


def build_tools_list_request(request_id: str) -> MCPRequest:
    """Собирает payload для метода tools/list."""
    return MCPRequest(id=request_id, method="tools/list", params={})


def build_tool_call_request(
    request_id: str, tool_name: str, arguments: Dict[str, Any]
) -> MCPRequest:
    """Собирает payload для метода tools/call."""
    return MCPRequest(
        id=request_id,
        method="tools/call",
        params={"name": tool_name, "arguments": arguments or {}},
    )
