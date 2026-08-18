"""
agent.py — Базовый асинхронный исполнитель (v2.4)

Чистый executor: цикл tool-calling + трейсинг + учёт токенов.
Отвечает исключительно за цикл tool-calling, трейсинг и возврат результата.
Не хранит глобальное состояние, не загружает промпты.
"""
from __future__ import annotations
import json
import logging
import inspect
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

from usage import UsageTracker


def _short_text(text: str, limit: int = 120) -> str:
    """Сжимает текст в одну строку с ограничением по длине (для логов)."""
    if not text:
        return ""
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= limit else one_line[:limit] + "…"


def _short_args(args: dict, max_total: int = 60) -> str:
    """Компактно форматирует аргументы вызова инструмента для логов."""
    if not args:
        return ""
    parts = [f"{k}={str(v)[:27] + '...' if len(str(v)) > 30 else str(v)!r}" for k, v in args.items()]
    s = ", ".join(parts)
    return s if len(s) <= max_total else s[: max_total - 3] + "..."


class Agent:
    """
    Чистый исполнитель. Получает всё готовым: client, prompt, tools, history.
    """
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        system_prompt: str,
        tools: List[Any],
        name: str = "agent",
        max_iterations: int = 15,
        temperature: float = 0.3,
        max_tokens: int = 16384,
        usage: Optional[UsageTracker] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Description: Инициализирует исполнителя с LLM-клиентом и инструментами.
        Input:
            - client (AsyncOpenAI): асинхронный LLM-клиент.
            - model (str): идентификатор модели.
            - system_prompt (str): системная инструкция агента.
            - tools (List): функции-инструменты с @tool.
            - name (str): имя агента (для логов и учёта токенов).
            - max_iterations (int): лимит итераций tool-calling.
            - temperature (float): температура генерации.
            - max_tokens (int): лимит токенов на ответ.
            - usage (UsageTracker): общий счётчик токенов.
            - logger (logging.Logger): логгер.
        Output: None.
        """
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.name = name
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.usage = usage or UsageTracker()
        self.log = logger or logging.getLogger("agent.worker")

        self.tools_schema = [
            getattr(t, "_tool_schema", {}) for t in tools if hasattr(t, "_tool_schema")
        ]
        self.router = {
            getattr(t, "_tool_name"): t for t in tools if hasattr(t, "_tool_name")
        }

    async def run(self, user_message: str, history: Optional[List[Dict]] = None) -> tuple[str, List[Dict]]:
        """
        Description: Основной цикл tool-calling для сообщения пользователя.
        Input:
            - user_message (str): запрос пользователя.
            - history (List[Dict]): история диалога ЭТОГО агента (без чужих system).
        Output:
            - tuple[str, List[Dict]]: финальный ответ и обновлённая история агента.
        """
        if not history:
            history = [{"role": "system", "content": self.system_prompt}]
        history.append({"role": "user", "content": user_message})

        self.log.info("▶️  [%s] %s", self.name, _short_text(user_message, 160))

        for iteration in range(self.max_iterations):
            self.log.debug("  [%s | итерация %d/%d]", self.name, iteration + 1, self.max_iterations)
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=history,
                    tools=self.tools_schema or None,
                    tool_choice="auto" if self.tools_schema else None,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception as e:
                self.log.error("❌ [%s] Ошибка API: %s", self.name, e)
                return f"❌ Ошибка API: {e}", history

            # --- Учёт токенов (как в одиночном агенте) ---
            self.usage.record(self.name, getattr(response, "usage", None))

            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            # Размышления перед вызовом инструментов
            if message.content and message.tool_calls:
                reasoning = _short_text(message.content, 140)
                if reasoning:
                    self.log.info("    💭 [%s] %s", self.name, reasoning)

            # --- Ветка без инструментов ---
            if not message.tool_calls:
                content = message.content or ""

                # Пустой ответ — мягкий «пинок»
                if finish_reason == "stop" and not content.strip():
                    self.log.warning("⚠️  [%s] Пустой ответ, пинаю…", self.name)
                    history.append({"role": "assistant", "content": ""})
                    history.append({"role": "user", "content": "[Система: предыдущий ответ был пустым. Продолжай.]"})
                    continue

                # Обрезанный ответ — просим продолжить
                if finish_reason == "length":
                    self.log.info("    ⚠️  [%s] Ответ обрезан, продолжаю…", self.name)
                    history.append({"role": "assistant", "content": content})
                    history.append({"role": "user", "content": "[Система: предыдущий ответ был обрезан. Продолжай с того места.]"})
                    continue

                history.append({"role": "assistant", "content": content})
                self.log.info("✅ [%s] Готово: %s", self.name, _short_text(content))
                return content, history

            # --- Ветка с вызовами инструментов ---
            history.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [tc.model_dump() for tc in message.tool_calls],
            })

            for tc in message.tool_calls:
                func_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                self.log.info("  🔧 [%s] %s(%s)", self.name, func_name, _short_args(args))

                if func_name in self.router:
                    try:
                        func = self.router[func_name]
                        if inspect.iscoroutinefunction(func):
                            result = await func(**args)
                        else:
                            result = func(**args)
                        result_text = str(result)
                    except Exception as e:
                        self.log.exception("  ❌ [%s] Ошибка инструмента %s", self.name, func_name)
                        result_text = f"❌ Ошибка выполнения: {e}"
                else:
                    self.log.error("  ❌ [%s] Инструмент '%s' не найден", self.name, func_name)
                    result_text = f"❌ Инструмент '{func_name}' не зарегистрирован"

                status = "✓" if not result_text.startswith("❌") else "✗"
                self.log.info("     %s %s | %d симв.", status, func_name, len(result_text))
                self.log.debug("   [%s] TOOL RESULT [%s]:\n%s", self.name, func_name, result_text)

                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text,
                })

        self.log.warning("⚠️  [%s] Превышен лимит итераций (%d)", self.name, self.max_iterations)
        history.append({
            "role": "assistant",
            "content": "⚠️ Превышен лимит итераций. Уточните или упростите задачу.",
        })
        return "⚠️ Превышен лимит итераций.", history