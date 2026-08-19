"""
interfaces/cli.py — Консольный интерфейс.
Version: 5.2.0
"""
import logging
import sys
from openai import OpenAI

from agent.core.mcp.sync_client import SyncMCPClient
from agent.core.tools.registry import ToolRegistry
from agent.orchestrator import Orchestrator
from config.settings import get_settings


def setup_logger(log_file: str):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(sh)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def run_cli():
    settings = get_settings()
    setup_logger(settings.log_file)
    logger = logging.getLogger("cli")

    print("🔄 Подключение к MCP Туту...")
    mcp_client = SyncMCPClient(url=settings.tutu_mcp_url)
    if not mcp_client.initialize():
        print("❌ Не удалось подключиться к MCP")
        return

    openai_client = OpenAI(
        api_key=settings.yandex_api_key,
        base_url=settings.yandex_base_url,
        project=settings.yandex_folder_id,
    )

    # ПЕРЕДАЁМ folder_id в ToolRegistry
    registry = ToolRegistry(
        openai_client=openai_client,
        folder_id=settings.yandex_folder_id,
        mcp_client=mcp_client,
    )

    orchestrator = Orchestrator(
        client=openai_client,
        folder_id=settings.yandex_folder_id,
        mcp_client=mcp_client,
        registry=registry,
        settings=settings,
    )

    print("=" * 60)
    print(f"🧳 Tutu Travel Agent v{settings.system_version} (CLI)")
    print(f"   Router: {settings.yandex_model_router}")
    print(f"   Agent:  {settings.yandex_model_agent}")
    print(f"   MCP:    {len(mcp_client.tool_names())} инструментов")
    print(f"   Log:    {settings.log_file}")
    print("   Команды: /exit /clear /usage")
    print("=" * 60)
    logger.info(f"CLI Session started | version={settings.system_version}")

    history = []
    while True:
        try:
            user_input = input("\n👤 Вы: ").strip()
            if not user_input:
                continue
            cmd = user_input.lower()
            if cmd in ("exit", "quit", "/exit"):
                print(f"\n{orchestrator.usage.summary()}")
                print("👋 До свидания!")
                break
            if cmd == "/clear":
                history = []
                print("🗑️ История очищена")
                continue
            if cmd == "/usage":
                print(f"\n{orchestrator.usage.summary()}")
                continue

            response = orchestrator.route_and_execute(user_input, history)
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})
            print(f"\n🤖 Агент:\n{response}")
        except KeyboardInterrupt:
            print(f"\n\n{orchestrator.usage.summary()}")
            print("\n👋 Принудительный выход")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            logger.exception("Critical error in CLI")


if __name__ == "__main__":
    run_cli()