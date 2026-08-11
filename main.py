"""
Tutu Travel Agent — точка входа.
Примеры:
python main.py --mode console                        # мультиагент, Chat Completions
python main.py --mode console --api-type responses   # мультиагент, Responses API
python main.py --mode api --host 0.0.0.0 --port 8000
"""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(log_file: str = "logs.txt") -> None:
    """
    Настройка логирования с ротацией файла.
    
    - Файловый лог (DEBUG): до 5 файлов по 5 МБ каждый.
    - Консоль: ОТКЛЮЧЕНА (только финальный результат выводится вручную).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Очистить старые обработчики (если логирование уже было настроено).
    root_logger.handlers.clear()
    
    # FileHandler с ротацией (5 файлов по 5 МБ).
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 МБ
        backupCount=5,
        encoding='utf-8',  # явно UTF-8 для файла
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    
    # Добавляем ТОЛЬКО файловый лог, консоль отключена
    root_logger.addHandler(file_handler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tutu Travel Agent")
    parser.add_argument(
        "--mode",
        choices=["console", "api", "websocket"],
        default="console",
        help="Режим запуска (по умолчанию: console)",
    )
    parser.add_argument("--host", default=None, help="Хост для API (по умолчанию из настроек)")
    parser.add_argument("--port", type=int, default=None, help="Порт для API (по умолчанию из настроек)")
    parser.add_argument(
        "--api-type",
        choices=["openai", "responses"],
        default="openai",
        help="API для LLM: openai (Chat Completions) или responses (Responses API)",
    )
    return parser.parse_args()


def run_console(api_type: str) -> int:
    """Запускает консольный чат (оркестратор сам выбирает специалистов)."""
    from interfaces.cli import main as cli_main
    return cli_main(api_type=api_type)


def run_api(host: str, port: int) -> int:
    """Запускает FastAPI-сервер."""
    import uvicorn
    from config import get_settings
    from interfaces.api.app import app

    settings = get_settings()
    host = host or settings.api_host
    port = port or settings.api_port

    print(f"🚀 Запуск FastAPI на http://{host}:{port}")
    print(f"   REST:   POST /chat, GET /health, GET /tools")
    print(f"   WebSocket: /ws (текст и голос)")
    
    uvicorn.run(app, host=host, port=port)
    return 0


def main() -> int:
    # Настройка логирования ДО всех остальных операций.
    setup_logging("logs.txt")
    
    args = parse_args()
    if args.mode == "console":
        return run_console(args.api_type)
    elif args.mode in ("api", "websocket"):
        return run_api(args.host, args.port)
    else:
        print(f"❌ Неизвестный режим: {args.mode}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
