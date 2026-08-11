"""
Асинхронный сборщик агентов (AgentBuilder).

Отвечает за сборку специалиста:
- единый AsyncOpenAI-клиент на все агенты (кэш);
- единый MCP-клиент и реестр инструментов (кэш);
- парсинг скиллов: YAML frontmatter (--- ... ---) И плоский заголовок `key: value`;
- фильтрация инструментов по списку `tools` из скилла (раздел 1.2);
- системный промпт = база (travel_assistant + mcp_instructions + mcp_tools_rules)
  + инструкция специалиста; дата всегда свежая — промпт пересобирается
  через system_prompt_provider на каждой итерации цикла.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml
import aiohttp
import openai

from config import get_settings
from tools.mcp.async_client import AsyncMCPClient
from tools.registry import ToolRegistry
from agents.prompts.prompt_loader import PromptLoader
from agents.specs import AgentSpec
from client.openai_agent import AsyncOpenAIAgent

_log = logging.getLogger("travel_agent.builder")

__all__ = ["AsyncAgentBuilder"]

# Скиллы, у которых нет файла-инструкции: генералист получает все инструменты.
_GENERAL_SKILLS = {"full", "general", ""}


class AsyncAgentBuilder:
    """Сборка агентов-специалистов с общими кэшированными ресурсами."""

    def __init__(
        self,
        settings=None,
        http_session: Optional[aiohttp.ClientSession] = None,
    ):
        self._settings = settings or get_settings()
        self._http_session = http_session
        self._owns_http_session = http_session is None
        self._mcp: Optional[AsyncMCPClient] = None
        self._skills_dir = Path(__file__).resolve().parent / "skills"
        self._prompt_loader = PromptLoader()
        self._registry: Optional[ToolRegistry] = None
        self._llm_client: Optional[openai.AsyncOpenAI] = None
        self._skills_cache: Dict[str, Tuple[Dict[str, Any], str]] = {}

    # ------------------------------------------------------------------
    # Ресурсы
    # ------------------------------------------------------------------
    async def _ensure_http(self) -> aiohttp.ClientSession:
        """Создаёт aiohttp-сессию, если её ещё нет или она закрыта."""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
            self._owns_http_session = True
        return self._http_session

    async def get_mcp(self) -> AsyncMCPClient:
        """Возвращает MCP-клиент. Кэш только после успешной инициализации."""
        if self._mcp is None:
            session = await self._ensure_http()
            client = AsyncMCPClient(
                url=self._settings.mcp_url,
                headers=self._settings.mcp_headers,
                logger=logging.getLogger("mcp"),
                settings=self._settings,
            )
            await client.initialize(session)
            # Кэшируем ТОЛЬКО после успешного рукопожатия,
            # иначе при ошибке в кэше останется сломанный клиент.
            self._mcp = client
        return self._mcp

    def get_llm_client(self) -> openai.AsyncOpenAI:
        """Единый AsyncOpenAI-клиент на все агенты."""
        if self._llm_client is None:
            self._llm_client = openai.AsyncOpenAI(
                api_key=self._settings.api_key,
                base_url=self._settings.yandex_base_url,
            )
        return self._llm_client

    async def get_registry(self) -> ToolRegistry:
        """Реестр инструментов: из MCP или статический fallback."""
        if self._registry is None:
            registry = ToolRegistry()
            tools = None
            try:
                mcp = await self.get_mcp()
                session = await self._ensure_http()
                tools = await mcp.list_tools(session)
            except Exception as e:
                _log.warning("MCP tools/list недоступен, переключаюсь на статику: %s", e)
            if tools:
                registry.load_from_mcp(tools)
            else:
                registry.load_static()
            self._registry = registry
        return self._registry

    # ------------------------------------------------------------------
    # Скиллы
    # ------------------------------------------------------------------
    def _parse_skill(self, skill_name: str) -> Tuple[Dict[str, Any], str]:
        """
        Разбирает agents/skills/<skill>.md на (метаданные, тело инструкции).

        Поддерживает два формата шапки:
        1) YAML frontmatter:   ---\\n name: ...\\n tools: [...]\\n ---\\n тело
        2) Плоский заголовок:  строки `key: value` до первой пустой строки/#.
        """
        skill_name = (skill_name or "").strip()
        if skill_name in self._skills_cache:
            return self._skills_cache[skill_name]
        if skill_name in _GENERAL_SKILLS:
            return {}, ""

        path = self._skills_dir / f"{skill_name}.md"
        if not path.exists():
            _log.warning("Файл скилла не найден: %s", path)
            self._skills_cache[skill_name] = ({}, "")
            return {}, ""

        # utf-8-sig автоматически убирает BOM, если файл сохранён с ним.
        content = path.read_text(encoding="utf-8-sig").strip()
        meta: Dict[str, Any] = {}
        body = content

        if content.startswith("---"):
            # Формат 1: классический YAML frontmatter.
            parts = content.split("---", 2)
            if len(parts) >= 3:
                if yaml is not None:
                    try:
                        meta = yaml.safe_load(parts[1]) or {}
                        if not isinstance(meta, dict):
                            meta = {}
                    except Exception as e:
                        _log.warning("YAML шапка скилла %s не распарсена: %s", skill_name, e)
                else:
                    _log.warning("PyYAML не установлен — шапка скилла %s пропущена", skill_name)
                body = parts[2].strip()
        else:
            # Формат 2: плоский заголовок `key: value` в начале файла.
            lines = content.splitlines()
            header_len = 0
            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    break
                header_len += 1
            if header_len:
                header_text = "\n".join(lines[:header_len])
                if yaml is not None:
                    try:
                        parsed = yaml.safe_load(header_text)
                        if isinstance(parsed, dict):
                            meta = parsed
                    except Exception as e:
                        _log.warning("Шапка скилла %s не распарсена: %s", skill_name, e)
                body = "\n".join(lines[header_len:]).strip()

        result = (meta, body)
        self._skills_cache[skill_name] = result
        return result

    async def _resolve_tools(self, spec: AgentSpec) -> List[Dict]:
        """
        Инструменты агента: специалист получает только инструменты скилла.
        Генералист (skill=full) получает весь реестр.
        extra_tools из specs добавляются поверх списка скилла.
        """
        registry = await self.get_registry()
        if spec.skill in _GENERAL_SKILLS:
            return registry.tools

        meta, _ = self._parse_skill(spec.skill)
        allowed = {str(t).strip() for t in (meta.get("tools") or []) if str(t).strip()}
        allowed |= {t for t in spec.extra_tools if t}

        if not allowed:
            _log.warning(
                "Скилл '%s' не объявил tools — агент [%s] получит все %d инструментов",
                spec.skill, spec.name, len(registry.tools),
            )
            return registry.tools

        # Сохраняем порядок реестра, отбирая только разрешённые имена.
        resolved = [t for t in registry.tools if t["function"]["name"] in allowed]
        missing = allowed - {t["function"]["name"] for t in resolved}
        if missing:
            _log.warning(
                "Инструменты из скилла '%s' не найдены в реестре: %s",
                spec.skill, sorted(missing),
            )
        if not resolved:
            _log.warning("Агент [%s] остался без инструментов — отдаю весь реестр", spec.name)
            return registry.tools

        _log.debug(
            "Агент [%s]: %d/%d инструментов (скилл '%s')",
            spec.name, len(resolved), len(registry.tools), spec.skill,
        )
        return resolved

    # ------------------------------------------------------------------
    # Сборка агента
    # ------------------------------------------------------------------
    async def build(
        self,
        spec: AgentSpec,
        logger: Optional[logging.Logger] = None,
    ) -> AsyncOpenAIAgent:
        """Собирает агента-специалиста по спецификации."""
        tools = await self._resolve_tools(spec)
        mcp = await self.get_mcp()
        _, skill_body = self._parse_skill(spec.skill)

        def make_system_prompt() -> str:
            """Свежий промпт на каждой итерации: база с актуальной датой + скилл."""
            base = self._prompt_loader.get_system_prompt()
            if skill_body:
                return f"{base}\n\n---\n\n# ИНСТРУКЦИЯ СПЕЦИАЛИСТА\n\n{skill_body}"
            return base

        common: Dict[str, Any] = dict(
            client=self.get_llm_client(),
            model=spec.model or self._settings.composite_model,
            mcp_client=mcp,
            tools=tools,
            max_iterations=spec.max_iterations,
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
            logger=logger,
        )

        # Responses API: промпт хранится на сервере Yandex под prompt_id.
        if spec.api_type == "responses":
            prompt_id = spec.prompt_id or self._settings.responses_prompt_id
            if prompt_id:
                from client.openai_responses_agent import AsyncResponsesAgent
                return AsyncResponsesAgent(prompt_id=prompt_id, **common)
            _log.warning(
                "Агент [%s]: api_type=responses, но prompt_id не задан — "
                "переключаюсь на Chat Completions", spec.name,
            )

        return AsyncOpenAIAgent(
            system_prompt=make_system_prompt(),
            system_prompt_provider=make_system_prompt,
            **common,
        )

    # ------------------------------------------------------------------
    # Жизненный цикл
    # ------------------------------------------------------------------
    async def close(self) -> None:
        """Закрывает все ресурсы. Чужую http-сессию не закрывает."""
        if self._mcp is not None:
            await self._mcp.close()
            self._mcp = None
        if self._llm_client is not None:
            await self._llm_client.close()
            self._llm_client = None
        # Чужую сессию (переданную извне) не закрываем.
        if self._owns_http_session and self._http_session is not None:
            await self._http_session.close()
            self._http_session = None