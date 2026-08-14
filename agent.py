# ============================================================
# Агент со скилами v1.2 (с поддержкой MCP Туту через SyncMCPClient)
# ============================================================
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
import yaml

# Импорт инструментов и MCP-клиента
from agent_tools import (
    create_all_tools,
    collect_tools,
    create_tool_router,
    load_skills_catalog,
    _short_args,
    _short_text,
)

# Попытка импорта MCP-клиента
try:
    from tools.mcp.client import SyncMCPClient
    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    print(f"⚠️ Модуль tools.mcp не найден или ошибка импорта: {e}. Инструменты Туту недоступны.")

load_dotenv()

# ============================================================
# Пути к файлам данных
# ============================================================
PROMPTS_FILE = Path(".agents/prompts/system.yaml")
LOG_FILE = Path(__file__).with_name("log.txt")

# ============================================================
# Логирование (трейсинг)
# ============================================================
def setup_logger() -> logging.Logger:
    """Настраивает логгер агента с двумя потоками вывода."""
    logger = logging.getLogger("agent")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(sh)
    return logger

logger = setup_logger()

# ============================================================
# Загрузка конфигурации агента
# ============================================================
def load_prompts() -> dict:
    """Загружает промпты и параметры генерации из YAML-файла."""
    if not PROMPTS_FILE.exists():
        raise FileNotFoundError(f"Файл промптов не найден: {PROMPTS_FILE}")
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ============================================================
# Инициализация: конфиг, клиент API, MCP, инструменты
# ============================================================
PROMPTS = load_prompts()
GENERATION = PROMPTS.get("generation", {})

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_MODEL = GENERATION.get("model", "yandexgpt/latest")
MODEL_URI = f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}"

# Клиент OpenAI для Яндекс AI Studio
client = OpenAI(
    api_key=YANDEX_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_FOLDER_ID,
)

# Инициализация MCP-клиента (Синхронный)
mcp_client = None
if MCP_AVAILABLE:
    try:
        mcp_client = SyncMCPClient(url="https://mcp.tutu.ru/mcp")
        if mcp_client.initialize():
            logger.info("✅ MCP-клиент (Туту) подключен")
        else:
            logger.warning("⚠️ MCP-клиент не инициализирован.")
            mcp_client = None
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации MCP: {e}")
        mcp_client = None
else:
    logger.warning("⚠️ Модуль tools.mcp не найден. Инструменты Туту недоступны.")

# Создание инструментов (базовые + Yandex + MCP)
ALL_TOOLS = create_all_tools(client, model_name=MODEL_URI, mcp_client=mcp_client)
TOOLS_SCHEMA = collect_tools(*ALL_TOOLS)
TOOL_ROUTER = create_tool_router(*ALL_TOOLS)

# ============================================================
# Сборка системного промпта (с инжекцией даты)
# ============================================================
def build_system_prompt() -> str:
    """Собирает системный промпт: база из YAML + каталог навыков + дата."""
    base = PROMPTS.get("system_prompt", "")
    catalog = load_skills_catalog()
    
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"][datetime.now().weekday()]
    date_context = (
        f"\n\n## Текущий контекст времени\n"
        f"Сегодня: **{today}** ({weekday}).\n"
        f"Все даты в запросах пользователя ('завтра', 'на следующей неделе') "
        f"считай относительно этой даты. Никогда не предлагай билеты на даты в прошлом.\n"
    )
    
    return (
        base 
        + date_context 
        + "\n\n## Каталог доступных навыков\n"
        + "(Выбери подходящий по колонке «когда использовать» и загрузи через load_skill.)\n\n" 
        + catalog
    )

# ============================================================
# Основной цикл агента
# ============================================================
def chat_with_agent(user_message: str, conversation_history: list = None):
    """Главный цикл агента: отправляет сообщение модели и обрабатывает вызовы инструментов."""
    logger.info("\n👤 %s", _short_text(user_message, 200))
    logger.debug("USER MESSAGE (full):\n%s", user_message)

    if conversation_history is None:
        conversation_history = []

    if not conversation_history:
        system_prompt = build_system_prompt()
        logger.debug("SYSTEM PROMPT:\n%s", system_prompt)
        conversation_history.append({"role": "system", "content": system_prompt})

    conversation_history.append({"role": "user", "content": user_message})
    logger.info("🤖 Агент думает...")

    temperature = float(GENERATION.get("temperature", 0.3))
    max_tokens = int(GENERATION.get("max_tokens", 16384))
    max_iterations = int(GENERATION.get("max_iterations", 25))

    cont_prompts = PROMPTS.get("continuation_prompts", {})
    empty_cont = cont_prompts.get("empty_response", "[Система: предыдущий ответ был пустым. Продолжай.]")
    truncated_cont = cont_prompts.get("truncated_response", "[Система: предыдущий ответ был обрезан. Продолжай с того места.]")

    for iteration in range(max_iterations):
        logger.info(f"  [{iteration + 1}/{max_iterations}]")
        
        response = client.chat.completions.create(
            model=MODEL_URI,
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

        # Размышления модели
        if message.content and message.tool_calls:
            logger.debug("MODEL REASONING (full):\n%s", message.content)
            short_reasoning = _short_text(message.content, 140)
            if short_reasoning:
                logger.info("    💭 %s", short_reasoning)

        # Аномалия: пустой ответ
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

        # Ответ обрезан
        if finish_reason == "length" and not message.tool_calls:
            logger.info("    ⚠️  Ответ обрезан, продолжаю...")
            logger.debug("TRUNCATED CONTENT (full):\n%s", message.content)
            conversation_history.append({"role": "assistant", "content": message.content or ""})
            conversation_history.append({"role": "user", "content": truncated_cont})
            continue

        # Финальный ответ
        if not message.tool_calls:
            logger.debug("FINAL ANSWER (full):\n%s", message.content)
            conversation_history.append({"role": "assistant", "content": message.content})
            return message.content, conversation_history

        # Выполнение tool_calls
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
            logger.debug("TOOL CALL: name=%s args=%s", func_name, json.dumps(func_args, ensure_ascii=False))

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

            logger.debug("TOOL RESULT [%s] full (%d chars):\n%s", func_name, len(result_text), result_text)
            status = "✓" if not result_text.startswith("❌") else "✗"
            logger.info("       %s %s | %d симв. (подробности в log.txt)", status, func_name, len(result_text))

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
    """Бесконечный цикл «вопрос-ответ» в консоли."""
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
        print(f"\n🤖 Агент:\n{response}\n")

# ============================================================
# Точка входа
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print(f"🚀 Новая сессия агента | лог: {LOG_FILE}")
    print("=" * 60)
    interactive_mode()
