"""
agent.py — Базовый асинхронный исполнитель (v2.3)
Отвечает исключительно за цикл tool-calling, трейсинг и возврат результата.
Не хранит глобальное состояние, не загружает промпты.
"""
from __future__ import annotations
import json
import logging
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

# Настройка логгера: работает автономно, но не конфликтует с корневым логгером из main.py
logger = logging.getLogger("agent.worker")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    logger.propagate = True  # Позволяет корневому логгеру из main.py обрабатывать сообщения
    
    # Фолбэк: если корневого логгера нет (запуск напрямую), добавляем свои хендлеры
    if not logging.getLogger().hasHandlers():
        LOG_DIR = Path("log")
        LOG_DIR.mkdir(exist_ok=True)
        LOG_FILE = LOG_DIR / "agent.log"
        
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(console_handler)


def _short_text(text: str, limit: int = 120) -> str:
    """Truncates text to a single line with a specified character limit."""
    if not text: 
        return ""
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= limit else one_line[:limit] + "…"


def _short_args(args: dict, max_total: int = 60) -> str:
    """Formats dictionary arguments into a compact string for logging."""
    if not args: 
        return ""
    parts = [f"{k}={str(v)[:27]+'...' if len(str(v))>30 else str(v)!r}" for k, v in args.items()]
    s = ", ".join(parts)
    return s if len(s) <= max_total else s[: max_total - 3] + "..."


class Agent:
    """
    Pure executor. Receives everything ready-made: client, prompt, tools, history.
    """
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        system_prompt: str,
        tools: List[Any],
        max_iterations: int = 15,
        temperature: float = 0.3,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Description: Initializes the Agent executor with LLM client and tools.
        Input data:
            - client (AsyncOpenAI): The asynchronous LLM client.
            - model (str): The model identifier (e.g., 'yandexgpt/latest').
            - system_prompt (str): The base system instruction for the agent.
            - tools (List[Any]): List of tool functions decorated with @tool.
            - max_iterations (int): Maximum tool-calling loop iterations.
            - temperature (float): LLM generation temperature.
            - logger (Optional[logging.Logger]): Custom logger instance.
        Output: None (Initializes instance attributes).
        """
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.log = logger or logging.getLogger(__name__)
        
        self.tools_schema = [
            getattr(t, "_tool_schema", {}) for t in tools if hasattr(t, "_tool_schema")
        ]
        self.router = {
            getattr(t, "_tool_name"): t for t in tools if hasattr(t, "_tool_name")
        }

    async def run(self, user_message: str, history: Optional[List[Dict]] = None) -> tuple[str, List[Dict]]:
        """
        Description: Executes the main tool-calling loop for a given user message.
        Input data:
            - user_message (str): The user's input query.
            - history (Optional[List[Dict]]): Existing conversation history.
        Output:
            - tuple[str, List[Dict]]: Final text response and updated conversation history.
        """
        if history is None:
            history = [{"role": "system", "content": self.system_prompt}]
        history.append({"role": "user", "content": user_message})
        
        self.log.info("▶️ Запуск агента. Сообщение: %s", _short_text(user_message))
        
        for iteration in range(self.max_iterations):
            self.log.debug("  [Итерация %d/%d]", iteration + 1, self.max_iterations)
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=history,
                    tools=self.tools_schema or None,
                    tool_choice="auto" if self.tools_schema else None,
                    temperature=self.temperature,
                )
            except Exception as e:
                self.log.error("❌ Ошибка Yandex AI Studio: %s", e)
                return f"❌ Ошибка API: {e}", history

            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            # 1. Финальный ответ без инструментов
            if not message.tool_calls:
                content = message.content or ""
                history.append({"role": "assistant", "content": content})
                self.log.info("✅ Завершено. Ответ: %s", _short_text(content))
                return content, history

            # 2. Есть вызовы инструментов
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
                
                self.log.info("  🔧 Вызов: %s(%s)", func_name, _short_args(args))
                
                if func_name in self.router:
                    try:
                        func = self.router[func_name]
                        # Поддержка как синхронных, так и асинхронных инструментов
                        if inspect.iscoroutinefunction(func):
                            result = await func(**args)
                        else:
                            result = func(**args)
                        result_text = str(result)
                    except Exception as e:
                        self.log.exception("  ❌ Ошибка в инструменте %s", func_name)
                        result_text = f"❌ Ошибка выполнения: {e}"
                else:
                    self.log.error("  ❌ Инструмент '%s' не найден в роутере", func_name)
                    result_text = f"❌ Инструмент '{func_name}' не зарегистрирован"
                
                self.log.debug("   Результат (%d симв.): %s", len(result_text), _short_text(result_text))
                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text
                })
                
        self.log.warning("⚠️ Превышен лимит итераций (%d)", self.max_iterations)
        history.append({
            "role": "assistant", 
            "content": "⚠️ Превышен лимит итераций. Пожалуйста, перефразируйте запрос или уточните задачу."
        })
        return "⚠️ Превышен лимит итераций.", history