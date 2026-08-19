"""
main.py — Универсальная точка входа в систему.
Version: 1.0.0
Description: Роутер между режимами запуска (CLI, API, Web).
Usage:
    python main.py                    # Запуск CLI (по умолчанию)
    python main.py --mode cli         # Запуск CLI
    python main.py --mode api         # Запуск FastAPI сервера
    python main.py --mode web         # Запуск веб-интерфейса (в разработке)
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Tutu Travel Agent — Мультиагентная система",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python main.py                      Запуск CLI (консольный чат)
  python main.py --mode api           Запуск FastAPI сервера (REST API)
  python main.py --mode web           Запуск веб-интерфейса (TODO)
  python main.py --help               Показать справку
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["cli", "api", "web"],
        default="cli",
        help="Режим запуска: cli (консоль), api (FastAPI), web (браузер)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Хост для API/Web сервера (по умолчанию: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Порт для API/Web сервера (по умолчанию: 8001)",
    )

    args = parser.parse_args()

    if args.mode == "cli":
        from interfaces.cli import run_cli
        run_cli()

    elif args.mode == "api":
        print("🚧 API режим в разработке (v2.0)")
        print("   В будущем здесь будет FastAPI сервер с REST endpoints:")
        print("   - POST /chat")
        print("   - GET /health")
        print("   - GET /tools")
        print("\n   Для запуска CLI используйте: python main.py --mode cli")
        sys.exit(0)

    elif args.mode == "web":
        print("🚧 Web режим в разработке (v2.0)")
        print("   В будущем здесь будет статическая HTML-страница с чатом.")
        print("\n   Для запуска CLI используйте: python main.py --mode cli")
        sys.exit(0)


if __name__ == "__main__":
    main()