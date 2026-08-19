"""
BaseAgent — движок агента с циклом tool-calling.
Version: 5.2.0
Description:
- Основной цикл агента (chat.completions API)
- Логирование токенов и времени через UsageTracker
- Красивый вывод tool_calls в консоль (с обрезкой длинных args)
- Полный DEBUG-трейс в logs.txt
- Обработка пустых и обрезанных ответов модели
"""
import json
import logging
import time
from typing import Dict, List, Optional


logger = logging.getLogger("agent.base")


class UsageTracker:
    """Накопитель статистики использования токенов за сессию."""

    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.request_count = 0
        self.total_time = 0.0

    def add(self, prompt: int, completion: int, duration: float):
        """Добавляет статистику по одному запросу."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.request_count += 1
        self.total_time += duration

    def summary(self) -> str:
        """Возвращает сводку по сессии."""
        return (
            f"📊 Сессия: {self.request_count} запросов | "
            f"⏱️ {self.total_time:.2f}s | "
            f"🔤 {self.prompt_tokens} in / {self.completion_tokens} out / {self.total_tokens} total"
        )


class BaseAgent:
    """Универсальный агент с циклом tool-calling для Yandex AI Studio."""

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
        temperature: float = 0.3,
        max_tokens: int = 16384,
    ):
        """
        Инициализация агента.

        Args:
            client: OpenAI-клиент для Яндекс AI Studio
            folder_id: Yandex folder ID
            model: имя модели (например, 'yandexgpt/latest')
            system_prompt: системный промпт
            tools_schema: список JSON-схем инструментов
            tool_router: словарь {имя_инструмента: функция}
            usage_tracker: общий трекер токенов (для накопления между агентами)
            role_name: имя агента для логирования (router / executor)
            temperature: температура генерации
            max_tokens: максимум исходящих токенов
        """
        self.client = client
        self.folder_id = folder_id
        self.model_uri = self._build_model_uri(model)
        self.model_name = model
        self.system_prompt = system_prompt
        self.tools_schema = tools_schema or []
        self.tool_router = tool_router or {}
        self.usage = usage_tracker or UsageTracker()
        self.role_name = role_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_model_uri(self, model: str) -> str:
        """Формирует полный model URI для Яндекс API: gpt://{folder_id}/{model}."""
        if model.startswith("gpt://") or model.startswith("ds://"):
            return model
        return f"gpt://{self.folder_id}/{model}"

    def run(self, user_message: str, history: List[Dict] = None, max_iterations: int = 10) -> str:
        """
        Запускает основной цикл агента.

        Args:
            user_message: сообщение пользователя
            history: история диалога (если пустая — создаётся заново с system_prompt)
            max_iterations: максимум итераций цикла tool-calling

        Returns:
            Финальный текстовый ответ агента.
        """
        history = history or []
        if not history:
            history.append({"role": "system", "content": self.system_prompt})
        history.append({"role": "user", "content": user_message})

        session_start = time.time()
        logger.info(f"🤖 [{self.role_name}] model={self.model_name} (uri={self.model_uri})")

        for i in range(max_iterations):
            logger.info(f"  [{self.role_name}] iteration {i + 1}/{max_iterations}")
            start_t = time.time()

            # ============================================================
            # 1. API-запрос к модели
            # ============================================================
            try:
                response = self.client.chat.completions.create(
                    model=self.model_uri,
                    messages=history,
                    tools=self.tools_schema if self.tools_schema else None,
                    tool_choice="auto" if self.tools_schema else None,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception as e:
                logger.error(f"❌ [{self.role_name}] API error: {e}")
                raise

            duration = time.time() - start_t
            msg = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            # ============================================================
            # 2. Учёт токенов
            # ============================================================
            usage = getattr(response, "usage", None)
            prompt_t = getattr(usage, "prompt_tokens", 0) if usage else 0
            compl_t = getattr(usage, "completion_tokens", 0) if usage else 0
            self.usage.add(prompt_t, compl_t, duration)
            logger.debug(
                f"  [{self.role_name}] tokens={prompt_t}+{compl_t} | "
                f"time={duration:.2f}s | finish={finish_reason}"
            )

            # ============================================================
            # 3. Размышления модели (reasoning перед tool_calls)
            # ============================================================
            if msg.content and msg.tool_calls:
                short_reason = " ".join(msg.content.split())[:140]
                logger.info(f"    💭 {short_reason}...")

            # ============================================================
            # 4. Финальный ответ (без инструментов)
            # ============================================================
            if finish_reason == "stop" and not msg.tool_calls:
                content = msg.content or ""
                # Аномалия: пустой ответ — пинаем модель
                if not content.strip():
                    logger.warning(f"⚠️ [{self.role_name}] пустой ответ — пинаю...")
                    history.append({"role": "assistant", "content": ""})
                    history.append({"role": "user", "content": "[Система: предыдущий ответ был пустым. Продолжай выполнение задачи.]"})
                    continue
                logger.info(
                    f"✅ [{self.role_name}] done in {time.time() - session_start:.2f}s "
                    f"(tokens {prompt_t}+{compl_t})"
                )
                return content

            # ============================================================
            # 5. Ответ обрезан по длине
            # ============================================================
            if finish_reason == "length" and not msg.tool_calls:
                logger.warning(f"⚠️ [{self.role_name}] ответ обрезан — продолжаю...")
                history.append({"role": "assistant", "content": msg.content or ""})
                history.append({
                    "role": "user",
                    "content": "[Система: предыдущий ответ был обрезан по длине. Продолжи ровно с места остановки, не повторяя уже написанное.]",
                })
                continue

            # ============================================================
            # 6. Выполнение tool_calls
            # ============================================================
            if msg.tool_calls:
                # Сохраняем сообщение с tool_calls в историю
                history.append(msg.model_dump())

                for tc in msg.tool_calls:
                    # --- 6.1 Парсинг аргументов ---
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    # --- 6.2 Красивый вывод в консоль (с обрезкой) ---
                    short_args_parts = []
                    for k, v in args.items():
                        sv = str(v)
                        if k == "code":
                            # Код обрезаем особенно сильно — это самый шумный аргумент
                            short_args_parts.append(f"{k}='<{len(sv)} симв.>'")
                        elif k == "args_json":
                            # JSON-строка туту — тоже может быть длинной
                            if len(sv) > 100:
                                short_args_parts.append(f"{k}='{sv[:97]}...'")
                            else:
                                short_args_parts.append(f"{k}='{sv}'")
                        elif len(sv) > 80:
                            short_args_parts.append(f"{k}={sv[:77]}...")
                        else:
                            short_args_parts.append(f"{k}={sv!r}")
                    short_args = ", ".join(short_args_parts)
                    if len(short_args) > 150:
                        short_args = short_args[:147] + "..."

                    logger.info(f"    🔧 {tc.function.name}({short_args})")
                    # Полный лог аргументов — только в файл (DEBUG)
                    logger.debug(f"    FULL ARGS: {json.dumps(args, ensure_ascii=False)[:2000]}")

                    # --- 6.3 Выполнение инструмента ---
                    func = self.tool_router.get(tc.function.name)
                    if func:
                        try:
                            result = func(**args)
                            status = "✓"
                        except Exception as e:
                            result = f"❌ Ошибка: {str(e)}"
                            status = "✗"
                            logger.exception(f"Ошибка в {tc.function.name}")
                    else:
                        result = f"❌ Инструмент не найден: {tc.function.name}"
                        status = "✗"

                    result_str = str(result)
                    logger.info(f"       {status} {tc.function.name} | {len(result_str)} симв.")
                    # Полный результат — в файл (DEBUG)
                    logger.debug(f"       FULL RESULT ({len(result_str)} симв.):\n{result_str[:3000]}")

                    # --- 6.4 Добавляем результат в историю ---
                    history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })

                # Продолжаем цикл — модель должна обработать результаты tool_calls
                continue

            # Ни tool_calls, ни stop — выходим
            break

        logger.error(f"❌ [{self.role_name}] превышено max_iterations ({max_iterations})")
        return f"❌ Превышено количество итераций ({max_iterations})."