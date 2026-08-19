"""
Реестр инструментов агента.
Version: 5.2.0
Description: Собирает все инструменты и передаёт folder_id в YandexTools.
"""
from openai import OpenAI
from agent.core.mcp.sync_client import SyncMCPClient
from agent.core.mcp.tutu_tools import build_tutu_tools
from agent.core.tools.agent_tools import (
    YandexTools, bash_execute, collect_tools, create_tool_router,
    file_read, file_write, filter_tools_for_skill, load_skill,
)


class ToolRegistry:
    def __init__(self, openai_client: OpenAI, folder_id: str, mcp_client: SyncMCPClient):
        self.openai_client = openai_client
        self.folder_id = folder_id
        self.mcp_client = mcp_client
        self._init_tools()

    def _init_tools(self):
        # YandexTools с folder_id → правильный model_uri
        yt = YandexTools(
            client=self.openai_client,
            folder_id=self.folder_id,
            model_name="qwen3.6-35b-a3b/latest",  # для tool-calling инструментов Яндекса
        )

        self.all_tools = [
            load_skill, bash_execute, file_read, file_write,
            yt.upload_file, yt.download_file, yt.list_files,
            yt.execute_code, yt.generate_image, yt.web_search,
        ]
        self.all_tools.extend(build_tutu_tools(self.mcp_client, mode="proxy"))

        self.schemas = collect_tools(*self.all_tools)
        self.router = create_tool_router(*self.all_tools)

    def get_tools_for_skill(self, skill_name: str):
        filtered = filter_tools_for_skill(self.all_tools, skill_name)
        return collect_tools(*filtered), create_tool_router(*filtered)