"""
OpenAI-агент (синхронный и асинхронный).
Реализует тонкие методы chat* / execute_tool* для цикла из BaseAgent.
Использует OpenAI-совместимый API Yandex и SyncMCPClient / AsyncMCPClient.

ВАЖНО:
Аргументы tool call парсятся напрямую из tc.function.arguments
(OpenAI API возвращает их так, БЕЗ обёртки в tool_name/arguments).
AsyncOpenAIAgent вызывает mcp.call_tool(tool_name, arguments)
БЕЗ передачи aiohttp-сессии — клиент создаёт её сам лениво.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from client.base import BaseAgent, LLMStep
from tools.mcp.sync_client import SyncMCPClient
from tools.mcp.async_client import AsyncMCPClient

logger = logging.getLogger("travel_agent.agent.openai")


class OpenAIAgent(BaseAgent):
    """Синхронный агент на базе OpenAI-совместимого API Yandex."""

    def __init__(
        self,
        client,
        model: str,
        system_prompt: str,
        mcp_client: SyncMCPClient,
        tools: Optional[List[Dict]] = None,
        max_iterations: int = 12,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        logger: Optional[logging.Logger] = None,
        system_prompt_provider: Optional[Callable[[], str]] = None,
    ):
        super().__init__(
            system_prompt=system_prompt,
            tools=tools or [],
            max_iterations=max_iterations,
            temperature=temperature,
            max_tokens=max_tokens,
            logger=logger,
            system_prompt_provider=system_prompt_provider,
        )
        self.client = client
        self.model = model
        self.mcp = mcp_client
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    # ------------------------------------------------------------------
    # Тонкие методы цикла (используются BaseAgent.run / run_async)
    # ------------------------------------------------------------------
    def _chat_sync(self, messages: List[Dict[str, Any]]) -> LLMStep:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=self.tools or None,
            tool_choice="auto",
        )
        self._log_tokens(response)
        return self.llm_step_from_openai(response.choices[0].message)

    async def _chat_async(self, messages: List[Dict[str, Any]]) -> LLMStep:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=self.tools or None,
            tool_choice="auto",
        )
        self._log_tokens(response)
        return self.llm_step_from_openai(response.choices[0].message)

    def _execute_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.mcp.call_tool(tool_name, arguments)

    async def _execute_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # КЛЮЧЕВАЯ СТРОКА: tool_name первым, БЕЗ сессии.
        # AsyncMCPClient создаёт aiohttp-сессию сам лениво.
        return await self.mcp.call_tool(tool_name, arguments)

    # ------------------------------------------------------------------
    # Логирование расходов токенов
    # ------------------------------------------------------------------
    def _log_tokens(self, response: Any) -> None:
        """Логирует использованные токены из ответа API."""
        if not hasattr(response, 'usage') or response.usage is None:
            return
        usage = response.usage
        input_tokens = getattr(usage, 'prompt_tokens', 0)
        output_tokens = getattr(usage, 'completion_tokens', 0)
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self.logger.info(
            f"💬 Токены: 📥 {input_tokens} (всего {self._total_input_tokens}) | "
            f"📤 {output_tokens} (всего {self._total_output_tokens}) | "
            f"∑ {input_tokens + output_tokens}"
        )

    def get_token_usage(self) -> Dict[str, int]:
        """Возвращает накопленные статистики токенов."""
        return {
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total": self._total_input_tokens + self._total_output_tokens,
        }


class AsyncOpenAIAgent(OpenAIAgent):
    """Асинхронный агент на базе AsyncOpenAI и AsyncMCPClient."""

    def __init__(
        self,
        client,
        model: str,
        system_prompt: str,
        mcp_client: AsyncMCPClient,
        tools: Optional[List[Dict]] = None,
        max_iterations: int = 12,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        logger: Optional[logging.Logger] = None,
        system_prompt_provider: Optional[Callable[[], str]] = None,
    ):
        super().__init__(
            client=client,
            model=model,
            system_prompt=system_prompt,
            mcp_client=mcp_client,
            tools=tools or [],
            max_iterations=max_iterations,
            temperature=temperature,
            max_tokens=max_tokens,
            logger=logger,
            system_prompt_provider=system_prompt_provider,
        )

    async def run(self, user_input: str, history: list) -> Tuple[str, list, list]:
        """
        Асинхронный запуск агента.
        Переопределяет синхронный BaseAgent.run: для async-агента единственный
        корректный путь — асинхронный цикл BaseAgent.run_async, который дёргает
        _chat_async / _execute_tool_async.
        """
        result = await self.run_async(user_input, history)
        # Логируем итоговый расход токенов при завершении цикла
        usage = self.get_token_usage()
        if usage["total"] > 0:
            self.logger.info(
                f"✅ Цикл завершён. Расход: 📥 {usage['input_tokens']} | "
                f"📤 {usage['output_tokens']} | ∑ {usage['total']}"
            )
        return result

    def run_sync(self, user_input: str, history: list) -> Tuple[str, list, list]:
        """Синхронный запуск для async-агента не поддерживается."""
        raise NotImplementedError(
            "AsyncOpenAIAgent поддерживает только асинхронный run(). "
            "Используйте OpenAIAgent для синхронного/консольного варианта."
        )

    