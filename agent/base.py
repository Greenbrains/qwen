"""
BaseAgent — движок агента с Responses API (Яндекс AI Studio).
Version: 5.2.0
Description: Основной цикл агента на базе client.responses.create() — новый официальный API Яндекса.
"""
import json
import logging
import time
from typing import Dict, List, Optional


logger = logging.getLogger("agent.base")


class UsageTracker:
    """Накопитель статистики использования за сессию."""

    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.request_count = 0
        self.total_time = 0.0

    def add(self, prompt: int, completion: int, duration: float):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.request_count += 1
        self.total_time += duration

    def summary(self) -> str:
        return (
            f"📊 Сессия: {self.request_count} запросов | "
            f"⏱️ {self.total_time:.2f}s | "
            f"🔤 {self.prompt_tokens} in / {self.completion_tokens} out / {self.total_tokens} total"
        )


class BaseAgent:
    """Универсальный агент на Responses API с циклом tool-calling."""

    def __init__(
        self,
        client,
        folder_id: str,
        model: str,
        system_prompt: str,
        tools_schema: Optional[list] = None,
        tool_router: Optional[dict] = None,
        usage_tracker: Optional[UsageTracker] = None,
        role_name: str = "agent",
    ):
        self.client = client
        self.folder_id = folder_id
        self.model_uri = self._build_model_uri(model)
        self.model_name = model
        self.system_prompt = system_prompt
        self.tools_schema = tools_schema or []
        self.tool_router = tool_router or {}
        self.usage = usage_tracker or UsageTracker()
        self.role_name = role_name

    def _build_model_uri(self, model: str) -> str:
        """Формирует gpt://{folder_id}/{model}."""
        if model.startswith("gpt://") or model.startswith("ds://"):
            return model
        return f"gpt://{self.folder_id}/{model}"

    def _format_tools_for_responses(self) -> List[Dict]:
        """Преобразует OpenAI-формат tools в Responses API формат (function)."""
        formatted = []
        for tool in self.tools_schema:
            if tool.get("type") == "function" and "function" in tool:
                formatted.append({
                    "type": "function",
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "parameters": tool["function"]["parameters"],
                })
        return formatted

    def run(self, user_message: str, history: List[Dict] = None, max_iterations: int = 10) -> str:
        history = history or []
        if not history:
            history.append({"role": "system", "content": self.system_prompt})
        history.append({"role": "user", "content": user_message})

        session_start = time.time()
        logger.info(f"🤖 [{self.role_name}] model={self.model_name} (uri={self.model_uri})")

        for i in range(max_iterations):
            logger.info(f"  [{self.role_name}] iteration {i + 1}/{max_iterations}")
            start_t = time.time()

            try:
                response = self.client.responses.create(
                    model=self.model_uri,
                    input=history,
                    instructions=self.system_prompt if i == 0 and not history[0]["role"] == "system" else "",
                    tools=self._format_tools_for_responses() if self.tools_schema else [],
                    temperature=0.3,
                )
            except Exception as e:
                logger.error(f"❌ [{self.role_name}] API error: {e}")
                raise

            duration = time.time() - start_t

            # Учёт токенов
            usage = getattr(response, "usage", None)
            prompt_t = getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0
            compl_t = getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0) or 0
            self.usage.add(prompt_t, compl_t, duration)
            logger.debug(
                f"  [{self.role_name}] tokens={prompt_t}+{compl_t} | time={duration:.2f}s"
            )

            # Извлекаем контент и tool_calls из output
            output = getattr(response, "output", []) or []
            text_parts = []
            tool_calls = []

            for item in output:
                item_type = getattr(item, "type", None)
                
                if item_type == "message":
                    for content in getattr(item, "content", []) or []:
                        if getattr(content, "type", None) == "output_text":
                            text_parts.append(getattr(content, "text", ""))
                
                elif item_type == "function_call":
                    tool_calls.append({
                        "call_id": getattr(item, "call_id", None),
                        "name": getattr(item, "name", ""),
                        "arguments": getattr(item, "arguments", "{}"),
                    })

            # Финальный ответ без инструментов
            if not tool_calls:
                final_text = "".join(text_parts).strip()
                if final_text:
                    logger.info(
                        f"✅ [{self.role_name}] done in {time.time() - session_start:.2f}s "
                        f"(tokens {prompt_t}+{compl_t})"
                    )
                    history.append({"role": "assistant", "content": final_text})
                    return final_text
                
                # Пустой ответ — пинаем
                logger.warning(f"⚠️ [{self.role_name}] пустой ответ — пинаю...")
                history.append({"role": "user", "content": "[Система: ответ был пустым. Продолжай.]"})
                continue

            # Есть tool_calls — выполняем
            if text_parts:
                reasoning = "".join(text_parts).strip()
                if reasoning:
                    short = reasoning[:140].replace("\n", " ")
                    logger.info(f"    💭 {short}...")

            # Добавляем в историю все tool_calls
            for tc in tool_calls:
                history.append({
                    "type": "function_call",
                    "call_id": tc["call_id"],
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                })

            for tc in tool_calls:
                try:
                    args = json.loads(tc["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}

                func = self.tool_router.get(tc["name"])
                if func:
                    try:
                        logger.info(f"    🔧 {tc['name']}({args})")
                        result = func(**args)
                        status = "✓"
                    except Exception as e:
                        result = f"❌ Ошибка: {str(e)}"
                        status = "✗"
                        logger.exception(f"Ошибка в {tc['name']}")
                else:
                    result = f"❌ Инструмент не найден: {tc['name']}"
                    status = "✗"

                logger.info(f"       {status} {tc['name']} | {len(str(result))} симв.")

                # Формат для Responses API: function_call_output
                history.append({
                    "type": "function_call_output",
                    "call_id": tc["call_id"],
                    "output": str(result),
                })

        logger.error(f"❌ [{self.role_name}] превышено max_iterations ({max_iterations})")
        return f"❌ Превышено количество итераций ({max_iterations})."