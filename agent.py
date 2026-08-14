# ============================================================
# Агент со скилами в 0.1.0
# ============================================================

import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import yaml
from tools import create_all_tools, collect_tools, create_tool_router, load_skills_catalog

load_dotenv()

# ============================================================
# Пути к файлам данных
# ------------------------------------------------------------
# Весь «контент» живёт вне кода: промпты — в YAML, навыки — в .md.
# Код только читает эти файлы при старте.
# ============================================================

PROMPTS_FILE = Path(".agents/prompts/system.yaml")
LOG_FILE = Path(__file__).with_name("log.txt")


# ============================================================
# Логирование (трейсинг)
# ============================================================

def setup_logger() -> logging.Logger:
    """Настраивает логгер агента с двумя потоками вывода.

    - Файл (log.txt), уровень DEBUG — полный трейс: системный промпт,
      размышления модели, полные результаты инструментов, токены, ошибки.
    - Консоль, уровень INFO — компактный «скелет» выполнения
      (шаги, имена инструментов, статусы), без технического шума.

    Возвращает настроенный логгер. Вызывается один раз при старте модуля.
    """
    logger = logging.getLogger("agent")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    # В файл — полный трейс с таймстампами
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    # В консоль — только сообщение, без префиксов уровня и времени
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(sh)

    return logger


logger = setup_logger()


# ============================================================
# Загрузка конфигурации агента (данные отделены от кода)
# ============================================================

def load_prompts() -> dict:
    """Загружает промпты и параметры генерации из YAML-файла.

    Всё «содержание» агента (системный промпт, запрос-самопрезентация,
    сообщения-пинки, temperature/max_tokens/max_iterations) живёт в
    .agents/prompts/system.yaml — поведение можно менять без правок кода.

    Возвращает словарь с ключами:
      - system_prompt          — базовый системный промпт;
      - self_intro_prompt      — запрос для пустого ввода (Enter);
      - continuation_prompts   — пинки при пустом/обрезанном ответе;
      - generation             — параметры генерации модели.

    Бросает FileNotFoundError, если файл отсутствует.
    """
    if not PROMPTS_FILE.exists():
        raise FileNotFoundError(
            f"Файл промптов не найден: {PROMPTS_FILE}\n"
            f"Создайте его по шаблону из документации."
        )
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# Инициализация: конфиг, клиент API, инструменты
# ============================================================

PROMPTS = load_prompts()
GENERATION = PROMPTS.get("generation", {})

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_MODEL = os.getenv("YANDEX_MODEL", "yandexgpt/latest")

# Клиент OpenAI-совместимого API Яндекс AI Studio
client = OpenAI(
    api_key=YANDEX_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_FOLDER_ID,
)

# Реестр инструментов: схемы для API + роутер имя->функция
ALL_TOOLS = create_all_tools(client)
TOOLS_SCHEMA = collect_tools(*ALL_TOOLS)
TOOL_ROUTER = create_tool_router(*ALL_TOOLS)


# ============================================================
# Сборка системного промпта
# ============================================================

def build_system_prompt() -> str:
    """Собирает системный промпт: база из YAML + каталог навыков с диска.

    База (общая дисциплина агента) берётся из system.yaml, затем
    дописывается актуальный каталог навыков из .agents/skills/SKILL.md.
    Поэтому добавление нового навыка не требует правок кода и промптов.
    """
    base = PROMPTS.get("system_prompt", "")
    catalog = load_skills_catalog()
    return (
        base
        + "\n\n## Каталог доступных навыков\n"
        + "(Выбери подходящий по колонке «когда использовать» и загрузи через load_skill.)\n\n"
        + catalog
    )


# ============================================================
# Вспомогательные функции форматирования (только для консоли)
# ------------------------------------------------------------
# В файл log.txt всегда пишется ПОЛНЫЙ текст; эти функции нужны,
# чтобы консоль оставалась читаемой.
# ============================================================

def _short_args(args: dict, max_total: int = 60) -> str:
    """Сжимает аргументы вызова инструмента в короткую строку для консоли.

    Каждое значение урезается до 30 символов, итоговая строка — до max_total.
    Пример: {'code': '<огромный скрипт>'} превратится в code='try: import open...'.
    Полные аргументы отдельно пишутся в log.txt на уровне DEBUG.
    """
    if not args:
        return ""
    parts = []
    for k, v in args.items():
        sv = str(v)
        if len(sv) > 30:
            sv = sv[:27] + "..."
        parts.append(f"{k}={sv!r}")
    s = ", ".join(parts)
    return s if len(s) <= max_total else s[:max_total - 3] + "..."


def _short_text(text: str, limit: int = 120) -> str:
    """Делает из текста однострочное превью без переносов для консоли.

    Склеивает все переносы и лишние пробелы в одну строку и урезает до limit.
    Используется для компактного показа сообщения пользователя
    и размышлений модели; полные тексты остаются в log.txt.
    """
    if not text:
        return ""
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= limit else one_line[:limit] + "…"


# ============================================================
# Основной цикл агента
# ============================================================

def chat_with_agent(user_message: str, conversation_history: list = None):
    """Главный цикл агента: отправляет сообщение модели и обрабатывает
    вызовы инструментов до получения финального ответа.

    На каждой итерации:
    1. Отправляет историю диалога в ЯндексGPT (Chat Completions + tool-calling).
    2. Разбирает finish_reason ответа:
       - "tool_calls"            — выполняет инструменты, результаты добавляет
                                   в историю и идёт на следующую итерацию;
       - "length" (пустой текст) — ответ обрезан по max_tokens: просит модель
                                   продолжить с места остановки;
       - "stop" (пустой текст)   — аномалия (модель «замолчала»): пинает её
                                   сообщением-пинком из YAML;
       - "stop" (с текстом)      — финальный ответ: возвращает его вызывающему.
    3. Защищён от зацикливания ограничением max_iterations.

    Args:
        user_message: текст запроса пользователя.
        conversation_history: история диалога; None — начать новый диалог
            (тогда первым сообщением добавляется системный промпт).

    Returns:
        Кортеж (финальный_ответ_модели, обновлённая_история).
    """
    logger.info("\n👤 %s", _short_text(user_message, 200))
    logger.debug("USER MESSAGE (full):\n%s", user_message)

    if conversation_history is None:
        conversation_history = []

    if not conversation_history:
        system_prompt = build_system_prompt()
        logger.debug("SYSTEM PROMPT:\n%s", system_prompt)
        conversation_history.append({
            "role": "system",
            "content": system_prompt,
        })

    conversation_history.append({
        "role": "user",
        "content": user_message,
    })

    logger.info("🤖 Агент думает...")

    # Параметры генерации и пинки берём из YAML-конфига
    temperature = float(GENERATION.get("temperature", 0.3))
    max_tokens = int(GENERATION.get("max_tokens", 16384))
    max_iterations = int(GENERATION.get("max_iterations", 25))

    cont_prompts = PROMPTS.get("continuation_prompts", {})
    empty_cont = cont_prompts.get(
        "empty_response",
        "[Система: предыдущий ответ был пустым. Продолжай.]",
    )
    truncated_cont = cont_prompts.get(
        "truncated_response",
        "[Система: предыдущий ответ был обрезан. Продолжай с того места.]",
    )

    for iteration in range(max_iterations):
        logger.info(f"  [{iteration + 1}/{max_iterations}]")
        logger.debug("--- Итерация %d/%d ---", iteration + 1, max_iterations)

        response = client.chat.completions.create(
            model=f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}",
            messages=conversation_history,
            tools=TOOLS_SCHEMA if TOOLS_SCHEMA else None,
            tool_choice="auto" if TOOLS_SCHEMA else None,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        logger.debug("   finish_reason: %s", finish_reason)
        if getattr(response, "usage", None):
            logger.debug(
                "TOKEN USAGE: prompt=%s completion=%s total=%s",
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                response.usage.total_tokens,
            )

        # Размышления модели (текст при tool_calls): в файл — полностью,
        # в консоль — одной короткой строкой
        if message.content and message.tool_calls:
            logger.debug("MODEL REASONING (full):\n%s", message.content)
            short_reasoning = _short_text(message.content, 140)
            if short_reasoning:
                logger.info("    💭 %s", short_reasoning)

        # Аномалия: finish_reason="stop", но текста и инструментов нет
        if finish_reason == "stop" and not message.tool_calls:
            content = message.content or ""
            if not content.strip():
                logger.warning("⚠️  Пустой ответ, пинаем...")
                conversation_history.append({"role": "assistant", "content": ""})
                conversation_history.append({"role": "user", "content": empty_cont})
                continue
            logger.debug("FINAL ANSWER (full):\n%s", content)
            conversation_history.append({"role": "assistant", "content": content})
            return content, conversation_history

        # Ответ обрезан по max_tokens — даём модели договорить
        if finish_reason == "length" and not message.tool_calls:
            logger.info("    ⚠️  Ответ обрезан, продолжаю...")
            logger.debug("TRUNCATED CONTENT (full):\n%s", message.content)
            conversation_history.append({
                "role": "assistant",
                "content": message.content or "",
            })
            conversation_history.append({"role": "user", "content": truncated_cont})
            continue

        # Нормальный финальный ответ без tool_calls
        if not message.tool_calls:
            logger.debug("FINAL ANSWER (full):\n%s", message.content)
            conversation_history.append({
                "role": "assistant",
                "content": message.content,
            })
            return message.content, conversation_history

        # Есть tool_calls — выполняем каждый и кладём результат в историю
        conversation_history.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [tc.model_dump() for tc in message.tool_calls],
        })

        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            try:
                func_args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                func_args = {}

            logger.info("    🔧 %s(%s)", func_name, _short_args(func_args))
            logger.debug(
                "TOOL CALL: name=%s args=%s",
                func_name,
                json.dumps(func_args, ensure_ascii=False),
            )

            if func_name in TOOL_ROUTER:
                try:
                    fn = TOOL_ROUTER[func_name]
                    result = fn(**func_args)
                    result_text = str(result)
                except Exception as e:
                    logger.exception("Ошибка выполнения инструмента %s", func_name)
                    result_text = f"❌ Ошибка выполнения: {str(e)}"
            else:
                logger.error("Инструмент '%s' не найден", func_name)
                result_text = f"❌ Инструмент '{func_name}' не найден"

            # В файл — полный результат; в консоль — только статус и размер
            logger.debug(
                "TOOL RESULT [%s] full (%d chars):\n%s",
                func_name, len(result_text), result_text,
            )
            status = "✓" if not result_text.startswith("❌") else "✗"
            logger.info(
                "       %s %s | %d симв. (подробности в log.txt)",
                status, func_name, len(result_text),
            )

            conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_text,
            })

    logger.error("Превышено max_iterations (%d)", max_iterations)
    return f"❌ Превышено максимальное количество итераций ({max_iterations})", conversation_history


# ============================================================
# Интерактивный режим
# ============================================================

def interactive_mode():
    """Бесконечный цикл «вопрос-ответ» в консоли.

    - 'exit' / 'quit' / 'выход' — завершение работы.
    - Пустой ввод (просто Enter) — подставляется self_intro_prompt из YAML:
      агент рассказывает о себе и генерирует серого кота, что за одно
      действие проверяет текстовый вывод, tool-calling и автосохранение
      файла в output/.
    """
    print("=" * 60)
    print("🚀 Агент с Яндекс AI Studio запущен")
    print("=" * 60)
    print("Доступные инструменты:")
    for tool_func in ALL_TOOLS:
        if hasattr(tool_func, '_tool_name'):
            print(f"  • {tool_func._tool_name}")
    print("=" * 60)
    print(f"📄 Промпты: {PROMPTS_FILE}")
    print(f"📄 Лог: {LOG_FILE}")
    print("Введите 'exit' для выхода")
    print("Нажмите Enter без текста — агент расскажет о себе\n")

    history = []
    self_intro = (PROMPTS.get("self_intro_prompt") or "").strip()

    while True:
        user_input = input("👤 Вы: ").strip()

        if user_input.lower() in ['exit', 'quit', 'выход']:
            print("👋 До свидания!")
            break

        if not user_input:
            user_input = self_intro
            print(f"   (→ {_short_text(user_input, 80)})")

        response, history = chat_with_agent(user_input, history)
        # Финальный ответ показываем целиком — это то, что ждёт пользователь
        print(f"\n🤖 Агент:\n{response}\n")


# ============================================================
# Точка входа
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print(f"🚀 Новая сессия агента | лог: {LOG_FILE}")
    print("=" * 60)
    interactive_mode()