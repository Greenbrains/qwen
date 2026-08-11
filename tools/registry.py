"""
Реестр инструментов. Хранит определения в формате OpenAI function tool.
Обёртка tutu_mcp УДАЛЕНА: агент парсит tool call напрямую.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from tools.mcp.models import MCPTool
from tools.definitions import ALL_TOOLS

logger = logging.getLogger("travel_agent.tools.registry")


class ToolRegistry:
    """Реестр доступных инструментов для модели."""

    def __init__(self):
        self._tools: List[Dict] = []
        self._source = "empty"

    def load_static(self) -> None:
        self._tools = list(ALL_TOOLS)
        self._source = "static"
        logger.debug(f"ToolRegistry loaded {len(self._tools)} static tools")

    def load_from_mcp(self, mcp_tools: List[MCPTool]) -> None:
        converted: List[Dict] = []
        for tool in mcp_tools:
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema
                        or {"type": "object", "properties": {}},
                    },
                }
            )
        self._tools = converted
        self._source = "mcp"
        logger.debug(f"ToolRegistry loaded {len(converted)} tools from MCP (no wrapper)")

    @property
    def tools(self) -> List[Dict]:
        return self._tools

    @property
    def source(self) -> str:
        return self._source

    def tool_names(self) -> List[str]:
        return [t["function"]["name"] for t in self._tools]

    def get_tool(self, name: str) -> Optional[Dict]:
        for t in self._tools:
            if t["function"]["name"] == name:
                return t
        return None

    def to_prompt_context(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
                "parameters": t["function"].get("parameters", {}),
            }
            for t in self._tools
        ]

    def clear(self) -> None:
        self._tools = []
        self._source = "empty"
        