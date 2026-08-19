"""
Реестр инструментов агента.
Версия: 2.2.0
Описание: Объединяет базовые инструменты, Яндекс AI Studio и MCP Туту.
"""
from openai import OpenAI

from agent.core.mcp.sync_client import SyncMCPClient
from agent.core.mcp.tutu_tools import build_tutu_tools
from agent.core.tools.agent_tools import (
    YandexTools,
    bash_execute,
    collect_tools,
    create_tool_router,
    file_read,
    file_write,
    filter_tools_for_skill,
    load_skill,
)


class ToolRegistry:
    """Реестр всех доступных инструментов агента."""

    def __init__(self, openai_client: OpenAI, mcp_client: SyncMCPClient):
        """Инициализация реестра с клиентами."""
        self.openai_client = openai_client
        self.mcp_client = mcp_client
        self._init_tools()

    def _init_tools(self):
        """Собирает все инструменты: базовые + Яндекс + MCP."""
        yt = YandexTools(self.openai_client, "yandexgpt/latest")
        self.all_tools = [
            load_skill, bash_execute, file_read, file_write,
            yt.upload_file, yt.execute_code, yt.web_search,
        ]
        self.all_tools.extend(build_tutu_tools(self.mcp_client, mode="proxy"))
        self.schemas = collect_tools(*self.all_tools)
        self.router = create_tool_router(*self.all_tools)

    def get_tools_for_skill(self, skill_name: str):
        """Возвращает схемы и роутер только для указанного навыка."""
        filtered_funcs = filter_tools_for_skill(self.all_tools, skill_name)
        return collect_tools(*filtered_funcs), create_tool_router(*filtered_funcs)