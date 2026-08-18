"""
agent_builder.py — Фабрика сборки агентов (v2.3)
Кэширует клиенты, парсит скиллы, фильтрует инструменты под конкретную задачу.
"""
from __future__ import annotations
import logging
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from openai import AsyncOpenAI

from tools.mcp.client import SyncMCPClient
from agent_tools import filter_tools_for_skill, create_all_tools

logger = logging.getLogger("agent.builder")


class AsyncAgentBuilder:
    """
    Factory class responsible for assembling configured Agent instances 
    with specific skills, tools, and MCP endpoints.
    """
    def __init__(self, api_key: str, base_url: str, model: str, skills_dir: str = ".agents/skills"):
        """
        Description: Initializes the Agent Builder with API credentials and paths.
        Input data:
            - api_key (str): Yandex AI Studio API key.
            - base_url (str): Base URL for the API endpoint.
            - model (str): Default model identifier.
            - skills_dir (str): Path to the directory containing skill definitions.
        Output: None (Initializes instance attributes).
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.skills_dir = Path(skills_dir)
        
        self._llm_client: Optional[AsyncOpenAI] = None
        self._mcp_clients: Dict[str, Any] = {}
        self._skills_cache: Dict[str, Tuple[Dict[str, Any], str]] = {}
        self._all_tools_cache: Optional[List[Any]] = None

    def get_llm_client(self) -> AsyncOpenAI:
        """
        Description: Lazily initializes and returns the AsyncOpenAI client.
        Input data: None.
        Output: AsyncOpenAI: The initialized asynchronous LLM client.
        """
        if self._llm_client is None:
            self._llm_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._llm_client

    async def get_mcp_client(self, name: str, url: str, headers: Optional[dict] = None) -> Any:
        """
        Description: Lazy initialization and caching of MCP clients to avoid redundant connections.
        Input data:
            - name (str): Identifier for the MCP service (e.g., 'tutu').
            - url (str): The MCP server endpoint URL.
            - headers (Optional[dict]): Optional HTTP headers for authentication.
        Output: Any: The initialized or cached MCP client instance.
        """
        if name not in self._mcp_clients:
            logger.info(f"🔌 Инициализация MCP-клиента: {name} ({url})")
            # ЗАМЕНИТЕ на реальный вызов вашего AsyncMCPClient при необходимости:
            # client = AsyncMCPClient(url=url, headers=headers)
            # await client.initialize()
            # self._mcp_clients[name] = client
            
            # Заглушка для демонстрации структуры
            self._mcp_clients[name] = {"name": name, "url": url, "status": "mock_initialized"}
        return self._mcp_clients[name]

    def parse_skill(self, skill_name: str) -> Tuple[Dict[str, Any], str]:
        """
        Description: Parses YAML frontmatter or flat header from a .md skill file.
        Input data:
            - skill_name (str): The name of the skill to load.
        Output: Tuple[Dict[str, Any], str]: A tuple containing metadata dictionary and the skill body text.
        """
        skill_name = (skill_name or "").strip()
        if not skill_name:
            return {}, ""
            
        if skill_name in self._skills_cache:
            return self._skills_cache[skill_name]
            
        path = self.skills_dir / f"{skill_name}.md"
        if not path.exists():
            logger.warning(f"Скилл '{skill_name}' не найден, использую пустой")
            self._skills_cache[skill_name] = ({}, "")
            return {}, ""
            
        content = path.read_text(encoding="utf-8-sig").strip()
        meta, body = {}, content
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    meta = yaml.safe_load(parts[1]) or {}
                except Exception as e:
                    logger.warning(f"Ошибка парсинга YAML в {skill_name}: {e}")
                body = parts[2].strip()
                
        self._skills_cache[skill_name] = (meta, body)
        return meta, body

    async def build(
        self,
        skill_name: str,
        custom_system_prompt: Optional[str] = None,
        extra_tools: Optional[List[str]] = None,
        mcp_endpoints: Optional[Dict[str, str]] = None,
    ) -> "Agent":
        """
        Description: Assembles and configures a specialized Agent instance based on the requested skill.
        Input data:
            - skill_name (str): The target skill identifier.
            - custom_system_prompt (Optional[str]): Override for the base system prompt.
            - extra_tools (Optional[List[str]]): Additional tool names to include.
            - mcp_endpoints (Optional[Dict[str, str]]): MCP services to connect.
        Output: Agent: A fully configured Agent instance ready for execution.
        """
        from agent import Agent 
        
        meta, skill_body = self.parse_skill(skill_name)
        
        # 1. Формируем системный промпт
        base_prompt = custom_system_prompt or "Ты — полезный ассистент."
        system_prompt = f"{base_prompt}\n\n---\n# ИНСТРУКЦИЯ СПЕЦИАЛИСТА\n{skill_body}" if skill_body else base_prompt
        
        # 2. Собираем инструменты (лениво, с кэшированием)
        if self._all_tools_cache is None:
            mcp_client = None
            if mcp_endpoints:
                first_mcp = list(mcp_endpoints.items())[0]
                mcp_client = await self.get_mcp_client(first_mcp[0], first_mcp[1])
                
            self._all_tools_cache = create_all_tools(
                client=self.get_llm_client(),
                model_name=self.model,
                mcp_client=mcp_client,
                mcp_mode="proxy"
            )
            
        # 3. Фильтруем инструменты под навык
        filtered_tools = filter_tools_for_skill(self._all_tools_cache, skill_name)
        if extra_tools:
            allowed_names = set(extra_tools) | {getattr(t, "_tool_name", "") for t in filtered_tools}
            filtered_tools = [t for t in self._all_tools_cache if getattr(t, "_tool_name", "") in allowed_names]
            
        logger.info(f"🏗️ Сборка агента: skill='{skill_name}', tools={len(filtered_tools)}")
        
        return Agent(
            client=self.get_llm_client(),
            model=self.model,
            system_prompt=system_prompt,
            tools=filtered_tools,
            logger=logger,
        )

    async def close(self):
        """
        Description: Gracefully closes all active MCP and LLM client connections.
        Input data: None.
        Output: None.
        """
        for client in self._mcp_clients.values():
            if hasattr(client, "close"):
                await client.close()
        if self._llm_client:
            await self._llm_client.close()