"""
Базовый класс агента.

Содержит ВСЮ общую логику агентного цикла:
- построение сообщений (system + history + user);
- парсинг и нормализация tool calls (включая обёртку
  {"tool_name": ..., "arguments": {...}} от единой функции tutu_mcp);
- форматирование результатов MCP-инструментов для модели (с подсказками
  для пустых offers/variants);
- retry при пустом финальном ответе;
- логирование и ограничение числа итераций.

Подкласс реализует только 4 тонких метода:
- _chat_sync / _chat_async          — один запрос к LLM -> LLMStep;
- _execute_tool_sync / _execute_tool_async — один вызов MCP -> dict.

Промпты (включая текущую дату) база НЕ содержит — они живут в core/prompts.
Системный промпт передаётся строкой (system_prompt) либо callable
(system_prompt_provider), который вызывается на каждом запуске цикла,
чтобы дата/переменные были всегда свежими.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("travel_agent.agent.base")

__all__ = ["BaseAgent", "LLMStep", "ToolCallInfo"]


# ----------------------------------------------------------------------
# Структуры данных шага
# ----------------------------------------------------------------------

@dataclass
class ToolCallInfo:
    """Нормализованный tool call из ответа LLM."""
    id: str
    name: str                      # внутреннее имя MCP-инструмента
    arguments: Dict[str, Any]      # аргументы MCP-инструмента
    raw_name: str = ""             # имя функции, как объявлено в tools[]
    raw_arguments: str = ""        # сырая строка arguments из ответа LLM


@dataclass
class LLMStep:
    """Один шаг ответа LLM: текст и/или tool calls."""
    content: str
    tool_calls: List[ToolCallInfo] = field(default_factory=list)
    finish_reason: Optional[str] = None


# ----------------------------------------------------------------------
# Базовый агент
# ----------------------------------------------------------------------

class BaseAgent:
    """
    Базовый агент с общим циклом «модель → tool calls → выполнение → модель».
    Синхронная и асинхронная версии цикла используют общие хелперы.
    """

    def __init__(
        self,
        system_prompt: str,
        tools: Optional[List[Dict]] = None,
        max_iterations: int = 12,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        logger: Optional[logging.Logger] = None,
        system_prompt_provider: Optional[Callable[[], str]] = None,
    ):
        self.system_prompt = system_prompt
        self.system_prompt_provider = system_prompt_provider
        self.tools = tools or []
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = logger or logging.getLogger("travel_agent.agent")
        # Кэш плейбуков (get_*_instructions) в рамках жизни агента.
        # Агенты переиспользуются оркестратором, поэтому повторный запрос
        # домена не будет заново тянуть инструкции из MCP.
        self._playbook_cache: Dict[str, str] = {}
        # Лимит на размер MCP-результата, уходящего в контекст LLM (символы).
        # 0 = без усечения. Большие ответы поиска (30k+) раздувают контекст
        # и замедляют генерацию; усечение бьёт по «хвосту» лишних офферов.
        self.max_tool_result_chars: int = 12000

    # ------------------------------------------------------------------
    # Тонкие методы для подклассов (переопределяются)
    # ------------------------------------------------------------------
    def _chat_sync(self, messages: List[Dict[str, Any]]) -> LLMStep:
        raise NotImplementedError("Подкласс должен реализовать _chat_sync()")

    async def _chat_async(self, messages: List[Dict[str, Any]]) -> LLMStep:
        raise NotImplementedError("Подкласс должен реализовать _chat_async()")

    def _execute_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Подкласс должен реализовать _execute_tool_sync()")

    async def _execute_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Подкласс должен реализовать _execute_tool_async()")

    # ------------------------------------------------------------------
    # Публичный интерфейс
    # ------------------------------------------------------------------
    def run(self, user_input: str, history: list) -> Tuple[str, list, list]:
        """Синхронный запуск агентного цикла."""
        messages = list(history or []) + [{"role": "user", "content": user_input}]
        tool_calls_log: List[Dict[str, Any]] = []
        self._log_loop_start(user_input, history or [])

        for iteration in range(1, self.max_iterations + 1):
            self.logger.debug(f"\n--- Iteration {iteration} ---")
            try:
                step = self._chat_sync(self._api_messages(messages))
            except Exception as e:
                self.logger.error(f"Agent loop exception: {e}", exc_info=True)
                return f"❌ Ошибка API: {e}", messages, tool_calls_log

            self._log_step(step)

            if step.tool_calls:
                messages.append(self._assistant_tool_calls_message(step))
                for tc in step.tool_calls:
                    result_text, log_entry = self._run_one_tool_sync(tc, iteration)
                    tool_calls_log.append(log_entry)
                    messages.append(self._tool_result_message(tc.id, result_text))
                continue

            final_text = step.content or ""
            if not final_text.strip() and tool_calls_log:
                final_text = self._retry_empty_sync(messages)

            self.logger.debug(f"Agent loop completed in {iteration} iterations")
            return final_text, messages, tool_calls_log

        self.logger.warning(f"Max iterations ({self.max_iterations}) exceeded")
        return f"⚠️ Превышено число итераций ({self.max_iterations})", messages, tool_calls_log

    async def run_async(self, user_input: str, history: list) -> Tuple[str, list, list]:
        """Асинхронный запуск агентного цикла."""
        messages = list(history or []) + [{"role": "user", "content": user_input}]
        tool_calls_log: List[Dict[str, Any]] = []
        self._log_loop_start(user_input, history or [])

        for iteration in range(1, self.max_iterations + 1):
            self.logger.debug(f"\n--- Iteration {iteration} ---")
            try:
                step = await self._chat_async(self._api_messages(messages))
            except Exception as e:
                self.logger.error(f"Async agent loop exception: {e}", exc_info=True)
                return f"❌ Ошибка API: {e}", messages, tool_calls_log

            self._log_step(step)

            if step.tool_calls:
                messages.append(self._assistant_tool_calls_message(step))
                for tc in step.tool_calls:
                    result_text, log_entry = await self._run_one_tool_async(tc, iteration)
                    tool_calls_log.append(log_entry)
                    messages.append(self._tool_result_message(tc.id, result_text))
                continue

            final_text = step.content or ""
            if not final_text.strip() and tool_calls_log:
                final_text = await self._retry_empty_async(messages)

            self.logger.debug(f"Async agent loop completed in {iteration} iterations")
            return final_text, messages, tool_calls_log

        self.logger.warning(f"Max iterations ({self.max_iterations}) exceeded")
        return f"⚠️ Превышено число итераций ({self.max_iterations})", messages, tool_calls_log

    async def stream(self, user_input: str, history: list) -> AsyncGenerator[str, None]:
        """Потоковая генерация. По умолчанию — полный ответ одним чанком."""
        final_text, _, _ = await self.run_async(user_input, history)
        yield final_text

    # ------------------------------------------------------------------
    # Общие хелперы цикла
    # ------------------------------------------------------------------
    def _get_system_prompt(self) -> str:
        """Свежий системный промпт: provider вызывается на каждом запуске."""
        if self.system_prompt_provider is not None:
            try:
                return self.system_prompt_provider()
            except Exception as e:
                self.logger.warning(f"system_prompt_provider failed: {e}")
        return self.system_prompt

    def _api_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [{"role": "system", "content": self._get_system_prompt()}] + messages

    @staticmethod
    def _assistant_tool_calls_message(step: LLMStep) -> Dict[str, Any]:
        """Сообщение assistant с tool_calls в формате OpenAI API."""
        return {
            "role": "assistant",
            "content": step.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.raw_name or tc.name,
                        "arguments": tc.raw_arguments or json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in step.tool_calls
            ],
        }

    @staticmethod
    def _tool_result_message(tool_call_id: str, content: str) -> Dict[str, Any]:
        return {"role": "tool", "tool_call_id": tool_call_id, "content": content}

    @staticmethod
    def _retry_prompt_message() -> Dict[str, Any]:
        return {
            "role": "user",
            "content": (
                "Ты получил результаты от инструментов, но не сформировал ответ. "
                "Пожалуйста, проанализируй результаты и дай пользователю полезный ответ. "
                "Если offers пустой — объясни это и предложи альтернативы."
            ),
        }

    # ------------------------------------------------------------------
    # Выполнение одного инструмента (sync / async)
    # ------------------------------------------------------------------
    def _run_one_tool_sync(self, tc: ToolCallInfo, iteration: int) -> Tuple[str, Dict[str, Any]]:
        self.logger.info(f"   🔧 [{tc.name}] args={json.dumps(tc.arguments, ensure_ascii=False)[:200]}")

        cached = self._playbook_cache_get(tc.name)
        if cached is not None:
            self.logger.info(f"   ⚡ [{tc.name}] из кэша плейбука (MCP-вызов пропущен)")
            return cached, {
                "tool": tc.name, "args": tc.arguments,
                "result_size": len(cached), "iteration": iteration, "cached": True,
            }

        try:
            result = self._execute_tool_sync(tc.name, tc.arguments)
        except Exception as e:
            self.logger.error(f"Tool execution error: {e}")
            result = {"error": str(e)}
        result_text = self.mcp_result_to_text(result, logger=self.logger)
        result_text = self._truncate_tool_result(tc.name, result_text)
        self.logger.debug(f"[{tc.name}] result size: {len(result_text)} chars")
        self.logger.debug(f"[{tc.name}] result preview: {result_text[:1500]}")
        self._playbook_cache_put(tc.name, result_text)
        log_entry = {
            "tool": tc.name,
            "args": tc.arguments,
            "result_size": len(result_text),
            "iteration": iteration,
        }
        return result_text, log_entry

    # ------------------------------------------------------------------
    # Кэш плейбуков и усечение результатов
    # ------------------------------------------------------------------
    @staticmethod
    def _is_playbook(tool_name: str) -> bool:
        """get_*_instructions — статические правила домена, кэшируемые."""
        return tool_name.startswith("get_") and tool_name.endswith("_instructions")

    def _playbook_cache_get(self, tool_name: str) -> Optional[str]:
        if self._is_playbook(tool_name):
            return self._playbook_cache.get(tool_name)
        return None

    def _playbook_cache_put(self, tool_name: str, result_text: str) -> None:
        if self._is_playbook(tool_name) and "Ошибка" not in result_text[:20]:
            self._playbook_cache[tool_name] = result_text

    def _truncate_tool_result(self, tool_name: str, text: str) -> str:
        """
        Усекает слишком большие результаты ПОИСКА перед подачей в LLM.
        Плейбуки и детали не трогаем — они нужны целиком.
        """
        limit = self.max_tool_result_chars
        if not limit or len(text) <= limit:
            return text
        if not tool_name.startswith("search_"):
            return text  # усечение только для поисковой выдачи
        head = text[:limit]
        self.logger.info(
            f"   ✂️ [{tool_name}] результат усечён {len(text)}→{limit} символов "
            "(лишние офферы отброшены для скорости генерации)"
        )
        return (
            head
            + "\n\n…[РЕЗУЛЬТАТ УСЕЧЁН] Показаны первые предложения. "
            "Их достаточно — выбери топ-3–5 лучших и не запрашивай остальные."
        )

    async def _run_one_tool_async(self, tc: ToolCallInfo, iteration: int) -> Tuple[str, Dict[str, Any]]:
        self.logger.info(f"   🔧 [{tc.name}] args={json.dumps(tc.arguments, ensure_ascii=False)[:200]}")

        # Кэш плейбуков: get_*_instructions не меняются в рамках сессии.
        cached = self._playbook_cache_get(tc.name)
        if cached is not None:
            self.logger.info(f"   ⚡ [{tc.name}] из кэша плейбука (MCP-вызов пропущен)")
            return cached, {
                "tool": tc.name, "args": tc.arguments,
                "result_size": len(cached), "iteration": iteration, "cached": True,
            }

        try:
            result = await self._execute_tool_async(tc.name, tc.arguments)
        except Exception as e:
            self.logger.error(f"Tool execution error: {e}")
            result = {"error": str(e)}
        result_text = self.mcp_result_to_text(result, logger=self.logger)
        result_text = self._truncate_tool_result(tc.name, result_text)
        self.logger.debug(f"[{tc.name}] result size: {len(result_text)} chars")
        self.logger.debug(f"[{tc.name}] result preview: {result_text[:1500]}")
        self._playbook_cache_put(tc.name, result_text)
        log_entry = {
            "tool": tc.name,
            "args": tc.arguments,
            "result_size": len(result_text),
            "iteration": iteration,
        }
        return result_text, log_entry

    # ------------------------------------------------------------------
    # Retry при пустом финальном ответе
    # ------------------------------------------------------------------
    def _retry_empty_sync(self, messages: list) -> str:
        self.logger.warning("Empty final response after tool calls. Triggering retry.")
        messages.append(self._retry_prompt_message())
        try:
            step = self._chat_sync(self._api_messages(messages))
            return step.content or "Извините, не удалось сформировать ответ."
        except Exception as e:
            self.logger.error(f"Retry failed: {e}")
            return "Извините, возникла техническая ошибка при формировании ответа."

    async def _retry_empty_async(self, messages: list) -> str:
        self.logger.warning("Empty final response after tool calls. Triggering retry.")
        messages.append(self._retry_prompt_message())
        try:
            step = await self._chat_async(self._api_messages(messages))
            return step.content or "Извините, не удалось сформировать ответ."
        except Exception as e:
            self.logger.error(f"Retry failed: {e}")
            return "Извините, возникла техническая ошибка при формировании ответа."

    # ------------------------------------------------------------------
    # Логирование
    # ------------------------------------------------------------------
    def _log_loop_start(self, user_input: str, history: list) -> None:
        self.logger.debug("=" * 60)
        self.logger.debug(f"AGENT LOOP START. User message: {user_input}")
        self.logger.debug(f"History length: {len(history)}")
        self.logger.debug("=" * 60)

    def _log_step(self, step: LLMStep) -> None:
        self.logger.debug(f"LLM response. Content: {(step.content or '')[:500]}")
        self.logger.debug(f"LLM response. Tool calls count: {len(step.tool_calls)}")

    # ------------------------------------------------------------------
    # Парсинг ответа OpenAI-совместимого API -> LLMStep
    # ------------------------------------------------------------------
    @classmethod
    def llm_step_from_openai(cls, message: Any) -> LLMStep:
        """
        Преобразует message из OpenAI-совместимого ответа в LLMStep.
        Нормализует обёртку {"tool_name": ..., "arguments": {...}}.
        """
        tool_calls: List[ToolCallInfo] = []
        for tc in (getattr(message, "tool_calls", None) or []):
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
            content=getattr(message, "content", None) or "",
            tool_calls=tool_calls,
            finish_reason=getattr(message, "finish_reason", None),
        )

    # ------------------------------------------------------------------
    # Нормализация аргументов tool call
    # ------------------------------------------------------------------
    @staticmethod
    def normalize_tool_arguments(raw_arguments: Any, fallback_name: str = "") -> Tuple[str, Dict[str, Any]]:
        """
        Приводит arguments tool call к (имя_инструмента, аргументы).
        Поддерживает обёртку единой функции:
            {"tool_name": "search_rail", "arguments": {...}}
        и прямой формат {...}.
        """
        if isinstance(raw_arguments, str):
            text = raw_arguments.strip()
            try:
                parsed = json.loads(text) if text else {}
            except json.JSONDecodeError:
                return fallback_name, {"raw": raw_arguments}
        else:
            parsed = raw_arguments or {}

        if not isinstance(parsed, dict):
            return fallback_name, {"value": parsed}

        if "tool_name" in parsed or "arguments" in parsed:
            name = parsed.get("tool_name") or fallback_name
            args = parsed.get("arguments") or {}
            if not isinstance(args, dict):
                args = {"value": args}
            return name, args

        return fallback_name, parsed

    # ------------------------------------------------------------------
    # Форматирование результата MCP для модели
    # ------------------------------------------------------------------
    @staticmethod
    def mcp_result_to_text(result: dict, logger: Optional[logging.Logger] = None) -> str:
        """
        Преобразует MCP result в читаемый текст для модели.
        Добавляет системные подсказки для пустых результатов.
        """
        _log = logger or logging.getLogger("travel_agent.agent")

        if "error" in result:
            return f"Ошибка: {result['error']}"

        content = result.get("content", [])
        if not content:
            return json.dumps(result, ensure_ascii=False, indent=2)

        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    text = item["text"]
                    try:
                        data = json.loads(text)
                        offers = data.get("offers", None)
                        if offers is not None and len(offers) == 0:
                            meta = data.get("meta", {})
                            hint = (
                                f"\n\n⚠️ [СИСТЕМА: offers пустой для маршрута "
                                f"{meta.get('from', {}).get('name', '?')} → "
                                f"{meta.get('to', {}).get('name', '?')}. "
                                f"ОБЯЗАТЕЛЬНО сообщи пользователю и предложи альтернативы "
                                f"(другие даты, другой транспорт)!]"
                            )
                            _log.debug("Empty offers detected. Hint added.")
                            parts.append(text + hint)
                            continue
                        variants = data.get("variants", None)
                        if variants is not None and len(variants) == 0:
                            _log.debug("Empty variants detected. Hint added.")
                            parts.append(
                                text + "\n\n⚠️ [СИСТЕМА: variants пустой. Предложи другие даты или транспорт!]"
                            )
                            continue
                    except (json.JSONDecodeError, TypeError):
                        pass
                    parts.append(text)
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))

        return "\n".join(parts)