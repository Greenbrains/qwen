"""
Pydantic-модели для JSON-RPC 2.0 и MCP-протокола.
Помощники для сборки запросов (initialize / tools/list / tools/call).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)


class MCPError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[MCPError] = None


class MCPTool(BaseModel):
    name: str
    description: Optional[str] = None
    inputSchema: Optional[Dict[str, Any]] = None


class MCPToolResult(BaseModel):
    content: List[Dict[str, Any]] = Field(default_factory=list)
    isError: bool = False
    structuredContent: Optional[Any] = None

    def as_text(self) -> str:
        parts = [c.get("text", "") for c in self.content if isinstance(c, dict) and c.get("text")]
        return "\n".join(parts)


def build_initialize_request(request_id, protocol_version, client_name, client_version) -> MCPRequest:
    return MCPRequest(
        id=request_id, method="initialize",
        params={
            "protocolVersion": protocol_version, "capabilities": {},
            "clientInfo": {"name": client_name, "version": client_version},
        },
    )


def build_tools_list_request(request_id) -> MCPRequest:
    return MCPRequest(id=request_id, method="tools/list", params={})


def build_tool_call_request(request_id, tool_name, arguments) -> MCPRequest:
    return MCPRequest(
        id=request_id, method="tools/call",
        params={"name": tool_name, "arguments": arguments or {}},
    )
