"""
SmartAgent — лайт-агент в обход оркестратора.
Один агент, все 16 MCP-инструментов, одна сессия.

Ключевое поведение:
- MCP-ответы НЕ копятся в памяти/истории — пишутся как заметки в notes.md.
- История между ходами «лёгкая»: только user + assistant (без tool-сообщений),
  поэтому контекст не раздувается до десятков тысяч токенов.
- Клиент LLM унифицирован через client/openai_agent (AsyncOpenAIAgent).
- Логируются время ответа и расход токенов.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import openai
import logging

from config import get_settings
from tools.mcp.async_client import AsyncMCPClient
from tools.registry import ToolRegistry
from agents.prompts.prompt_loader import PromptLoader
from client.openai_agent import AsyncOpenAIAgent

logger = logging.getLogger("travel_agent.smart")


class SmartAgent:
    """Лайт-агент: один, со всеми 16 инструментами, одна сессия."""

    def __init__(self, settings=None, notes_file: str = "notes.md"):
        self.settings = settings or get_settings()
        self.notes_file = Path(notes_file)
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.mcp_client: Optional[AsyncMCPClient] = None
        self.registry: Optional[ToolRegistry] = None
        self.agent: Optional[AsyncOpenAIAgent] = None
        # Одна сессия: лёгкая история (только user + assistant).
        self.history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Инициализация
    # ------------------------------------------------------------------
    async def initialize(self) -> None:
        logger.info("Инициализация SmartAgent...")

        # 1) HTTP-сессия для MCP-клиента (initialize/list_tools требуют её позиционно)
        self.http_session = aiohttp.ClientSession()

        # 2) MCP-клиент
        self.mcp_client = AsyncMCPClient(
            url=self.settings.mcp_url,
            headers=self.settings.mcp_headers,
            logger=logger,
            settings=self.settings,
        )
        await self.mcp_client.initialize(self.http_session)

        # 3) Реестр инструментов (все 16 из tools/list, fallback — статика)
        self.registry = ToolRegistry()
        tools = await self.mcp_client.list_tools(self.http_session)
        if tools:
            self.registry.load_from_mcp(tools)
        else:
            self.registry.load_static()
        logger.info(f"Загружено инструментов: {len(self.registry.tools)}")

        # 4) Промпт из md-файла (свежая дата)
        loader = PromptLoader()
        system_prompt = loader.get_system_prompt()

        # 5) LLM-клиент (унификация через client/openai_agent)
        client = openai.AsyncOpenAI(
            api_key=self.settings.api_key,
            base_url=self.settings.yandex_base_url,
            project=self.settings.yandex_folder_id,
        )

        self.agent = AsyncOpenAIAgent(
            client=client,
            model=self.settings.composite_model,
            system_prompt=system_prompt,
            mcp_client=self.mcp_client,
            tools=self.registry.tools,
            max_iterations=self.settings.max_agent_iterations,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            logger=logger,
        )
        logger.info("SmartAgent готов")

    # ------------------------------------------------------------------
    # Один ход диалога
    # ------------------------------------------------------------------
    async def ask(self, user_input: str) -> str:
        start = time.perf_counter()
        final_text, _messages, tool_calls = await self.agent.run_async(
            user_input, self.history
        )
        elapsed = time.perf_counter() - start

        # MCP-ответы не храним в памяти — пишем заметкой в md.
        self._write_note(user_input, final_text, tool_calls)

        # Лёгкая история: только user + assistant (tool-сообщения не копим).
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": final_text})

        usage = self.agent.get_token_usage()
        logger.info(
            f"✅ Ответ за {elapsed:.1f}s | "
            f"📥 {usage['input_tokens']} | 📤 {usage['output_tokens']} | ∑ {usage['total']}"
        )
        return final_text

    # ------------------------------------------------------------------
    # Заметки
    # ------------------------------------------------------------------
    def _write_note(
        self, user_input: str, final_text: str, tool_calls: List[Dict[str, Any]]
    ) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        lines = [f"\n---\n\n## 📝 {ts}", f"**Запрос:** {user_input}"]
        if tool_calls:
            names = ", ".join(tc.get("tool", "?") for tc in tool_calls)
            lines.append(f"\n🔧 Инструменты: {names}")
        lines.append(f"\n**Ответ:**\n\n{final_text}\n")
        with open(self.notes_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info(f"Заметка записана в {self.notes_file}")

    # ------------------------------------------------------------------
    # Завершение
    # ------------------------------------------------------------------
    async def close(self) -> None:
        if self.mcp_client is not None:
            await self.mcp_client.close()
        if self.http_session is not None:
            await self.http_session.close()
        logger.info("SmartAgent остановлен")