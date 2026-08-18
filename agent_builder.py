"""
agent_builder.py — Фабрика сборки агентов (v2.4)

Кэширует LLM/MCP-клиенты, парсит скиллы, фильтрует инструменты под задачу.
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from openai import AsyncOpenAI

from agent_tools import filter_tools_for_skill, create_all_tools
from usage import UsageTracker

if TYPE_CHECKING:
    from agent import Agent   # только для аннотаций типов, без рантайм-импорта

logger = logging.getLogger("agent.builder")

# Реальные endpoint'ы MCP-серверов по имени.
MCP_ENDPOINTS = {
    "tutu": "https://mcp.tutu.ru/mcp",
}


class AsyncAgentBuilder:
    """Фабрика: собирает настроенные экземпляры Agent под конкретный навык."""

    def __init__(self, api_key: str, base_url: str, model: str, skills_dir: str = ".agents/skills"):
        """
        Description: Инициализирует фабрику агентов.
        Input:
            - api_key (str): ключ Yandex AI Studio.
            - base_url (str): базовый URL API.
            - model (str): идентификатор модели по умолчанию.
            - skills_dir (str): путь к каталогу навыков.
        Output: None.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.skills_dir = Path(skills_dir)

        self._llm_client: Optional[AsyncOpenAI] = None
        self._mcp_clients: Dict[str, Any] = {}
        self._skills_cache: Dict[str, Tuple[Dict[str, Any], str]] = {}
        self._tools_cache: Optional[List[Any]] = None

    def get_llm_client(self) -> AsyncOpenAI:
        """Лениво создаёт и возвращает AsyncOpenAI-клиент."""
        if self._llm_client is None:
            self._llm_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._llm_client

    def get_mcp_client(self, name: str) -> Any:
        """
        Description: Ленивое создание и кэширование реального MCP-клиента.
        Input:
            - name (str): идентификатор сервиса ('tutu').
        Output: Any: инициализированный SyncMCPClient или None при сбое.
        """
        if name in self._mcp_clients:
            return self._mcp_clients[name]

        url = MCP_ENDPOINTS.get(name)
        if not url:
            logger.warning("Неизвестный MCP-сервис: %s", name)
            return None

        try:
            from tools.mcp.client import SyncMCPClient
            logger.info("🔌 Инициализация MCP-клиента: %s (%s)", name, url)
            client = SyncMCPClient(url=url)
            if client.initialize():
                self._mcp_clients[name] = client
                logger.info("✅ MCP '%s' подключён", name)
                return client
            logger.warning("⚠️ MCP '%s' не инициализирован", name)
        except Exception as e:
            logger.error("❌ Ошибка инициализации MCP '%s': %s", name, e)
        self._mcp_clients[name] = None
        return None

    def parse_skill(self, skill_name: str) -> Tuple[Dict[str, Any], str]:
        """
        Description: Парсит YAML-frontmatter или тело .md-файла навыка.
        Input:
            - skill_name (str): имя навыка.
        Output: Tuple[Dict, str]: метаданные и текст навыка.
        """
        skill_name = (skill_name or "").strip()
        if not skill_name:
            return {}, ""
        if skill_name in self._skills_cache:
            return self._skills_cache[skill_name]

        # Поддерживаем и .agents/skills/<name>/<name>.md, и .agents/skills/<name>.md
        candidates = [
            self.skills_dir / skill_name / f"{skill_name}.md",
            self.skills_dir / f"{skill_name}.md",
        ]
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            logger.warning("Скилл '%s' не найден, использую пустой", skill_name)
            self._skills_cache[skill_name] = ({}, "")
            return {}, ""

        content = path.read_text(encoding="utf-8-sig").strip()
        meta, body = {}, content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    import yaml
                    meta = yaml.safe_load(parts[1]) or {}
                except Exception as e:
                    logger.warning("Ошибка YAML в %s: %s", skill_name, e)
                body = parts[2].strip()

        self._skills_cache[skill_name] = (meta, body)
        return meta, body

    def _all_tools(self, mcp_endpoints: Optional[Dict[str, str]]) -> List[Any]:
        """Лениво собирает и кэширует полный набор инструментов (с MCP)."""
        if self._tools_cache is not None:
            return self._tools_cache

        mcp_client = None
        if mcp_endpoints:
            first = next(iter(mcp_endpoints))       # берём имя, url из MCP_ENDPOINTS
            mcp_client = self.get_mcp_client(first)

        self._tools_cache = create_all_tools(
            client=self.get_llm_client(),
            model_name=self.model,
            mcp_client=mcp_client,
            mcp_mode="proxy",
        )
        return self._tools_cache

    async def build(
        self,
        agent_name: str,
        skill_name: str,
        custom_system_prompt: Optional[str] = None,
        extra_tools: Optional[List[str]] = None,
        mcp_endpoints: Optional[Dict[str, str]] = None,
        usage: Optional[UsageTracker] = None,
    ) -> "Agent":
        """
        Description: Собирает и настраивает специализированного агента под навык.
        Input:
            - agent_name (str): имя агента (для логов/учёта токенов).
            - skill_name (str): целевой навык.
            - custom_system_prompt (str): переопределение базового промпта.
            - extra_tools (List[str]): дополнительные имена инструментов.
            - mcp_endpoints (Dict): требуемые MCP-сервисы.
            - usage (UsageTracker): общий счётчик токенов.
        Output: Agent: готовый к запуску экземпляр.
        """
        from agent import Agent

        _, skill_body = self.parse_skill(skill_name)

        base_prompt = custom_system_prompt or "Ты — полезный ассистент. Отвечай кратко и по делу, экономь токены."
        system_prompt = (
            f"{base_prompt}\n\n---\n# ИНСТРУКЦИЯ СПЕЦИАЛИСТА\n{skill_body}"
            if skill_body else base_prompt
        )

        all_tools = self._all_tools(mcp_endpoints)
        filtered = filter_tools_for_skill(all_tools, skill_name)
        if extra_tools:
            allowed = set(extra_tools) | {getattr(t, "_tool_name", "") for t in filtered}
            filtered = [t for t in all_tools if getattr(t, "_tool_name", "") in allowed]

        logger.info("🏗️  Сборка агента '%s': skill=%s, tools=%d", agent_name, skill_name, len(filtered))

        return Agent(
            client=self.get_llm_client(),
            model=self.model,
            system_prompt=system_prompt,
            tools=filtered,
            name=agent_name,
            usage=usage,
            logger=logging.getLogger(f"agent.{agent_name}"),
        )

    async def close(self):
        """Корректно закрывает MCP- и LLM-клиенты."""
        for client in self._mcp_clients.values():
            if client and hasattr(client, "close"):
                try:
                    client.close()
                except Exception:
                    pass
        if self._llm_client:
            await self._llm_client.close()