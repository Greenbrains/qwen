#!/usr/bin/env python3
"""
Tutu Travel Agent v4.0 — Мультиагентная система с каталогом скиллов.
Версия: main_v4.0

Запуск:
    python main.py [--mode console]

Логирование:
    - В файл logs.txt (с подсчётом токенов и времени)
    - В консоль не выводится
"""
from __future__ import annotations
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import get_settings
from agents.specs import DEFAULT_TEAM
from agents.orchestrator import AsyncOrchestrator
from client.memory import MemoryStore

# ======================================================================
# Настройка логгирования (только в файл, без консоли)
# ======================================================================
LOG_FILE = "logs.txt"

def setup_logging() -> logging.Logger:
    """Настраивает логгирование в файл с подсчётом токенов и времени."""
    logger = logging.getLogger("travel_agent")
    logger.setLevel(logging.DEBUG)
    
    # Очищаем существующие обработчики
    logger.handlers.clear()
    
    # File handler — только в файл
    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# ======================================================================
# Консольный интерфейс
# ======================================================================
class ConsoleCLI:
    """Простой консольный чат с агентом."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.settings = get_settings()
        self.memory = MemoryStore(db_path="data/memory.db")
        self.orchestrator: Optional[AsyncOrchestrator] = None
        self.history = []
        self.last_agent = None
        
    async def init(self):
        """Инициализация оркестратора."""
        self.orchestrator = AsyncOrchestrator(
            specs=DEFAULT_TEAM,
            settings=self.settings,
            memory=self.memory
        )
        self.logger.info("🚀 Travel Agent v4.0 запущен")
        self.logger.info(f"📋 Доступные агенты: {', '.join(self.orchestrator.team)}")
        
    async def process_query(self, user_input: str) -> str:
        """Обработка запроса пользователя."""
        if not self.orchestrator:
            await self.init()
        
        start_time = datetime.now()
        
        try:
            response, new_history, tools_used, agent_name = await self.orchestrator.run(
                user_input=user_input,
                history=list(self.history),
                last_agent=self.last_agent,
                user_alias="user"
            )
            
            self.history = new_history
            self.last_agent = agent_name
            
            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"⏱️ Обработка заняла {elapsed:.2f}s | Агент: {agent_name} | Инструменты: {len(tools_used)}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки запроса: {e}", exc_info=True)
            return f"Произошла ошибка: {e}"
    
    async def close(self):
        """Закрытие ресурсов."""
        if self.orchestrator:
            await self.orchestrator.close()
        if self.memory:
            self.memory.close()
        self.logger.info("🛑 Travel Agent остановлен")


async def chat_loop():
    """Основной цикл консольного чата."""
    logger = setup_logging()
    cli = ConsoleCLI(logger)
    
    print("=" * 60)
    print("🧳 Tutu Travel Agent v4.0 — Консольный режим")
    print("=" * 60)
    print("Команды:")
    print("  /help  — показать справку")
    print("  /clear — очистить историю")
    print("  /log   — показать путь к файлу логов")
    print("  /exit  — выход")
    print("=" * 60)
    
    await cli.init()
    
    try:
        while True:
            try:
                user_input = input("\n👤 Вы: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                break
            
            if not user_input:
                continue
            
            cmd = user_input.lower()
            if cmd in ("/exit", "/quit", "/q"):
                break
            elif cmd == "/help":
                print("📋 Доступные команды: /help, /clear, /log, /exit")
                continue
            elif cmd == "/clear":
                cli.history = []
                cli.last_agent = None
                print("🗑️ История очищена")
                continue
            elif cmd == "/log":
                log_path = Path(LOG_FILE).resolve()
                print(f"📄 Файл логов: {log_path}")
                continue
            
            # Обработка запроса
            print("🤖 Агент печатает...", end="\r")
            response = await cli.process_query(user_input)
            print(" " * 50, end="\r")  # Очистить строку
            print(f"🤖 Агент: {response}")
            
    finally:
        await cli.close()


def main():
    """Точка входа."""
    # Проверка аргументов командной строки
    mode = "console"
    if len(sys.argv) > 1 and sys.argv[1] in ("console", "api", "websocket"):
        mode = sys.argv[1]
    
    if mode != "console":
        print(f"⚠️ Режим '{mode}' пока не поддерживается в v4.0. Используйте console.")
        mode = "console"
    
    # Запуск основного цикла
    if mode == "console":
        asyncio.run(chat_loop())
    else:
        print(f"❌ Неизвестный режим: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
