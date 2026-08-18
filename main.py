"""
main.py — точка входа в мультиагентную систему v2.3
"""
import asyncio
import os
import sys
import logging 
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# 1. ЦЕНТРАЛИЗОВАННАЯ НАСТРОЙКА ЛОГИРОВАНИЯ
# Должна быть ВЫШЕ импортов модулей, чтобы они подхватили настройки
# ============================================================
LOG_DIR = Path("log")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "agent_log.md"

# Настраиваем корневой логгер (применяется ко всем модулям проекта)
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers.clear()  # Очищаем стандартные обработчики

# Файловый обработчик (пишет всё от DEBUG и выше)
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
root_logger.addHandler(file_handler)

# Консольный обработчик (выводит только WARNING и ERROR, чтобы не спамить)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING) 
console_handler.setFormatter(logging.Formatter("%(message)s"))
root_logger.addHandler(console_handler)
# ============================================================

load_dotenv()

from agent_builder import AsyncAgentBuilder
from orchestrator import AsyncOrchestrator

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
        "extra_tools": []
    },
    "marketingskills": {
        "description": "Продуктовый маркетинг: анализ конкурентов, SEO, позиционирование",
        "skill": "marketingskills",
        "mcp": [],
        "extra_tools": ["web_search", "execute_code", "file_write"]
    },
    "general": {
        "description": "Универсальный помощник для общих задач",
        "skill": "general",
        "mcp": [],
        "extra_tools": []
    }
}

async def run_interactive():
    builder = AsyncAgentBuilder(
        api_key=YANDEX_API_KEY,
        base_url=BASE_URL,
        model=MODEL_URI,
        skills_dir=".agents/skills"
    )
    orchestrator = AsyncOrchestrator(builder=builder, available_agents=AGENTS_CONFIG)
    
    print("=" * 10)
    print("🚀 MULTI-AGENT SYSTEM v2.3")
    print("=" * 10)
    print("📋 Специалисты:")
    for name, cfg in AGENTS_CONFIG.items():
        print(f"   • {name}: {cfg['description']}")
    print("=" * 10)
    print("💡 'exit' — выход, 'help' — справка")
    print(f"📁 Логи: {LOG_DIR.absolute()}")
    print()
    
    try:
        while True:
            try:
                user_input = input("👤 Вы: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n")
                break
            
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "выход"]:
                print("👋 До свидания!")
                break
            if user_input.lower() in ["help", "помощь", "?"]:
                print("\n📖 Справка:")
                print("  • Напишите запрос — Оркестратор выберет агента")
                print("  • 'clear' — очистить историю")
                print("  • 'exit' — завершить работу\n")
                continue
            if user_input.lower() == "clear":
                orchestrator.history = []
                print("🗑️ История очищена.\n")
                continue
            
            try:
                response, _ = await orchestrator.run(user_input)
                # \n дает пустую строку после ввода пользователя, .strip() убирает лишние пробелы
                print(f"\n🤖 Агент: {str(response).strip()}\n")
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
    finally:
        await orchestrator.close()

if __name__ == "__main__":  # <--- ИСПРАВЛЕНО: было if name == "main":
    asyncio.run(run_interactive())