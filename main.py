"""
main.py — точка входа мультиагентной системы (v2.4)

Единое место настройки логирования (консоль + файл) и учёта токенов.
При выходе печатает итоговый отчёт по токенам за сессию.
"""
import asyncio
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# 1. ЦЕНТРАЛИЗОВАННОЕ ЛОГИРОВАНИЕ (до импортов модулей проекта)
# ============================================================
LOG_DIR = Path("log")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "agent_log.md"

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers.clear()

# Файл: полный трейс (DEBUG) — включая TOKENS и TOOL RESULT.
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
root_logger.addHandler(file_handler)

# Консоль: INFO — итерации, вызовы инструментов, роутинг, токены за ход.
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))
root_logger.addHandler(console_handler)

# Приглушаем болтливые библиотеки.
for noisy in ("httpx", "httpcore", "openai", "urllib3", "requests"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
# ============================================================

load_dotenv()

from agent_builder import AsyncAgentBuilder      # noqa: E402
from orchestrator import AsyncOrchestrator       # noqa: E402
from usage import UsageTracker                   # noqa: E402

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_MODEL = os.getenv("YANDEX_MODEL", "yandexgpt/latest")
BASE_URL = "https://ai.api.cloud.yandex.net/v1"
MODEL_URI = f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}"

AGENTS_CONFIG = {
    "touragent": {
        "description": "Поиск туров, авиа/жд билетов, отелей через MCP Туту",
        "skill": "touragent",
        "mcp": ["tutu"],
        "extra_tools": [],
    },
    "marketingskills": {
        "description": "Продуктовый маркетинг: анализ конкурентов, SEO, позиционирование",
        "skill": "marketingskills",
        "mcp": [],
        "extra_tools": ["web_search", "execute_code", "file_write"],
    },
    "general": {
        "description": "Универсальный помощник для общих задач",
        "skill": "general",
        "mcp": [],
        "extra_tools": [],
    },
}


async def run_interactive():
    usage = UsageTracker()
    builder = AsyncAgentBuilder(
        api_key=YANDEX_API_KEY,
        base_url=BASE_URL,
        model=MODEL_URI,
        skills_dir=".agents/skills",
    )
    orchestrator = AsyncOrchestrator(
        builder=builder,
        available_agents=AGENTS_CONFIG,
        usage=usage,
    )

    print("=" * 52)
    print("🚀 MULTI-AGENT SYSTEM v3.0")
    print("=" * 52)
    print("📋 Специалисты:")
    for name, cfg in AGENTS_CONFIG.items():
        print(f"   • {name}: {cfg['description']}")
    print("=" * 52)
    print("💡 'exit' — выход | 'clear' — очистить историю | 'usage' — токены")
    print(f"📁 Логи: {LOG_FILE.absolute()}")
    print()

    try:
        while True:
            try:
                user_input = input("👤 Вы: ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if not user_input:
                continue
            low = user_input.lower()
            if low in ("exit", "quit", "выход"):
                break
            if low in ("help", "помощь", "?"):
                print("\n📖 Просто напишите запрос — оркестратор выберет агента.")
                print("   'clear' — очистить историю, 'usage' — токены, 'exit' — выход\n")
                continue
            if low == "clear":
                orchestrator.clear()
                print("🗑️  История очищена.\n")
                continue
            if low == "usage":
                print("\n" + usage.report() + "\n")
                continue

            try:
                response, agent_name = await orchestrator.run(user_input)
                print(f"\n🤖 [{agent_name}]: {str(response).strip()}\n")
            except Exception as e:
                logging.getLogger("agent.main").exception("Ошибка обработки запроса")
                print(f"\n❌ Ошибка: {e}\n")
    finally:
        # Итоговый отчёт по токенам за сессию — то, чего не хватало.
        print("\n" + usage.report())
        await orchestrator.close()
        print("👋 До свидания!")


if __name__ == "__main__":
    asyncio.run(run_interactive())