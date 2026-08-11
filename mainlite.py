"""
mainlite.py — запуск SmartAgent (лайт) в обход оркестратора.
Четыре фиксированных запроса: электрички, поезда, самолёты, отели.
"""
import asyncio
import logging
from logging.handlers import RotatingFileHandler

from config import get_settings
from smart_agent import SmartAgent


def setup_logging(log_file: str = "logs.txt") -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console)


QUESTIONS = [
    "электричка москва калуга на завтра",
    "поезд москва тула на завтра",
    "самолет москва анталья на 10 августа",
    "отели в казани 4 звезды с 15 августа на 1 день на одного",
]


async def main() -> None:
    setup_logging()
    settings = get_settings()
    settings.validate_llm()

    agent = SmartAgent(settings=settings, notes_file="notes.md")
    try:
        logging.info("Инициализация SmartAgent...")
        await agent.initialize()
        for q in QUESTIONS:
            print(f"\n{'=' * 60}\n👤 {q}\n{'=' * 60}")
            answer = await agent.ask(q)
            print(f"\n{answer}\n")
    except Exception:
        logging.exception("Ошибка в mainlite")
    finally:
        await agent.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До встречи!")