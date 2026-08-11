"""
Yandex Responses API агент (синхронный и асинхронный).
Использует client.responses.create() с prompt_id вместо передачи
системного промпта в каждом запросе.

ОТЛИЧИЯ ОТ Chat Completions API (openai_agent.py):
Промпт хранится на сервере Yandex (создаётся через API/console)
В запрос передаётся только prompt_id + input
История диалога передаётся через параметр input
Формат ответа отличается (response.output_text вместо choices[0].message)

ПРЕИМУЩЕСТВА:
Промпт не передаётся в каждом запросе (экономия токенов)
Промпт хранится централизованно на сервере
Версионирование промптов

НЕДОСТАТКИ:
Требуется предварительное создание промпта через API/console
Меньше гибкости в динамическом изменении промпта

ИНСТРУКЦИЯ ПО СОЗДАНИЮ ПРОМПТА:
Через Yandex Cloud Console:
DataSphere → Prompts → Create prompt
Или через API: POST /prompts с содержимым из travel_assistant.md + mcp_instructions.md + mcp_tools_rules.md
Получить prompt_id (формат: "fvt1s90v3a4k2grhr2i2")
Передать в Settings.responses_prompt_id или через переменную окружения RESPONSES_PROMPT_ID
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from client.base import BaseAgent, LLMStep, ToolCallInfo
from tools.mcp.sync_client import SyncMCPClient
from tools.mcp.async_client import AsyncMCPClient

logger = logging.getLogger("travel_agent.agent.responses")


class ResponsesAgent(BaseAgent):
    """Синхронный агент на базе Yandex Responses API."""

    def __init__(
        self,
        client,
        model: str,
        prompt_id: str,
        mcp_client: SyncMCPClient,
        tools: Optional[List[Dict]] = None,
        max_iterations: int = 12,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            client: OpenAI-совместимый клиент Yandex
            model: модель (например, "gpt://b1gd8itqunasnf56lij4/qwen3.6-35b-a3b/latest")
            prompt_id: ID промпта из Yandex (например, "fvt1s90v3a4k2grhr2i2")
            mcp_client: синхронный MCP-клиент
            tools: список инструментов в формате OpenAI function tool
            max_iterations: максимальное число итераций агентного цикла
            temperature: температура генерации
            max_tokens: максимальное число токенов в ответе
            logger: логгер
        """
        # BaseAgent требует system_prompt, но мы его не используем
        super().__init__(
            system_prompt="",  # не используется в Responses API
            tools=tools or [],
            max_iterations=max_iterations,
            temperature=temperature,
            max_tokens=max_tokens,
            logger=logger,
        )
        self.client = client
        self.model = model
        self.prompt_id = prompt_id
        self.mcp = mcp_client

    # ------------------------------------------------------------------
    # Тонкие методы цикла (используются BaseAgent.run / run_async)
    # ------------------------------------------------------------------
    def _api_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Responses API хранит системный промпт на сервере (prompt_id),
        поэтому НЕ добавляем system-сообщение в начало."""
        return messages

    def _chat_sync(self, messages: List[Dict[str, Any]]) -> LLMStep:
        response = self.client.responses.create(
            prompt={"id": self.prompt_id},
            input=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=self.tools or None,
            tool_choice="auto",
        )
        return self._llm_step_from_responses(response)

    async def _chat_async(self, messages: List[Dict[str, Any]]) -> LLMStep:
        response = await self.client.responses.create(
            prompt={"id": self.prompt_id},
            input=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=self.tools or None,
            tool_choice="auto",
        )
        return self._llm_step_from_responses(response)

    def _execute_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.mcp.call_tool(tool_name, arguments)

    async def _execute_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self.mcp.call_tool(tool_name, arguments)

    # ------------------------------------------------------------------
    # Преобразование ответа Responses API -> LLMStep
    # ------------------------------------------------------------------
    @classmethod
    def _llm_step_from_responses(cls, response) -> LLMStep:
        """Преобразует ответ Responses API в LLMStep."""
        tool_calls: List[ToolCallInfo] = []
        for tc in (getattr(response, "tool_calls", None) or []):
            raw_name = tc.function.name
            raw_arguments = tc.function.arguments
            name, args = cls.normalize_tool_arguments(raw_arguments, fallback_name=raw_name)
            tool_calls.append(
                ToolCallInfo(
                    id=tc.id,
                    name=name,
                    arguments=args,
                    raw_name=raw_name,
                    raw_arguments=raw_arguments,
                )
            )
        return LLMStep(
            content=getattr(response, "output_text", None) or "",
            tool_calls=tool_calls,
            finish_reason=getattr(response, "finish_reason", None),
        )


class AsyncResponsesAgent(ResponsesAgent):
    """Асинхронный агент на базе AsyncOpenAI и Responses API."""

    def __init__(
        self,
        client,
        model: str,
        prompt_id: str,
        mcp_client: AsyncMCPClient,
        tools: Optional[List[Dict]] = None,
        max_iterations: int = 12,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(
            client=client,
            model=model,
            prompt_id=prompt_id,
            mcp_client=mcp_client,
            tools=tools or [],
            max_iterations=max_iterations,
            temperature=temperature,
            max_tokens=max_tokens,
            logger=logger,
        )

    async def run(self, user_input: str, history: list) -> Tuple[str, list, list]:
        """
        Асинхронный запуск агента.
        Переопределяет синхронный BaseAgent.run: для async-агента единственный
        корректный путь — асинхронный цикл BaseAgent.run_async.
        """
        return await self.run_async(user_input, history)

    def run_sync(self, user_input: str, history: list) -> Tuple[str, list, list]:
        """Синхронный запуск не поддерживается для асинхронного агента."""
        raise NotImplementedError(
            "AsyncResponsesAgent поддерживает только асинхронный run(). "
            "Используйте ResponsesAgent для консоли."
        )

    