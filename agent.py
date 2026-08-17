# ============================================================
# Агент со скилами v2 — движок + класс Agent (мультиагент-ready)
#
# Ключевые улучшения относительно v1.3:
#  1. Экономия токенов: MCP подключается прокси-инструментом tutu_call
#     (не 16 схем на каждый шаг), а короткий каталог Туту инжектится в
#     системный промпт один раз. Плюс — учёт токенов (session usage).
#  2. Класс Agent: переиспользуемый исполнитель со своими system_prompt,
#     набором инструментов и параметрами генерации. Готов к оркестрации.
#  3. Устойчивость: корректная обработка finish_reason, tool-ошибок, MCP.
# ============================================================
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import OpenAI

from agent_tools import (
    collect_tools,
    create_all_tools,
    create_tool_router,
    filter_tools_for_skill,
    load_skills_catalog,
    _short_args,
    _short_text,
)

try:
    from tools.mcp import SyncMCPClient, tutu_catalog_markdown_fallback
    MCP_AVAILABLE = True
except ImportError as e:  # noqa
    MCP_AVAILABLE = False
    print(f"⚠️ tools.mcp недоступен: {e}. Инструменты Туту отключены.")

load_dotenv()

PROMPTS_FILE = Path(".agents/prompts/system.yaml")
LOG_FILE = Path(__file__).with_name("log.txt")


# ============================================================
# Логирование
# ============================================================
def setup_logger() -> logging.Logger:
    logger = logging.getLogger("agent")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(sh)
    return logger


logger = setup_logger()


# ============================================================
# Конфиг
# ============================================================
def load_prompts() -> dict:
    if not PROMPTS_FILE.exists():
        raise FileNotFoundError(f"Файл промптов не найден: {PROMPTS_FILE}")
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def date_context_block() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"][
        datetime.now().weekday()
    ]
    return (
        f"\n\n## Текущий контекст времени\n"
        f"Сегодня: **{today}** ({weekday}).\n"
        f"Все относительные даты ('завтра', 'на следующей неделе') считай от этой даты. "
        f"Никогда не предлагай варианты на прошедшие даты.\n"
    )


# ============================================================
# Класс Agent — переиспользуемый исполнитель
# ============================================================
class Agent:
    """Автономный агент: system_prompt + набор инструментов + цикл tool-calling.

    Пригоден как для одиночного использования, так и в роли агента-исполнителя
    в мультиагентной системе (оркестратор задаёт system_prompt и tools).
    """

    def __init__(
        self,
        client: OpenAI,
        model_uri: str,
        system_prompt: str,
        tool_functions: list,
        generation: dict = None,
        name: str = "agent",
    ):
        self.client = client
        self.model_uri = model_uri
        self.name = name
        self.system_prompt = system_prompt
        self.tools_schema = collect_tools(*tool_functions)
        self.router = create_tool_router(*tool_functions)

        g = generation or {}
        self.temperature = float(g.get("temperature", 0.3))
        self.max_tokens = int(g.get("max_tokens", 16384))
        self.max_iterations = int(g.get("max_iterations", 25))
        self.empty_cont = (g.get("continuation_prompts", {}) or {}).get(
            "empty_response", "[Система: предыдущий ответ был пустым. Продолжай.]"
        )
        self.truncated_cont = (g.get("continuation_prompts", {}) or {}).get(
            "truncated_response", "[Система: ответ был обрезан. Продолжай с места остановки.]"
        )
        # накопленный расход токенов за сессию агента
        self.usage = {"prompt": 0, "completion": 0, "total": 0, "calls": 0}

    def _account(self, resp):
        u = getattr(resp, "usage", None)
        if not u:
            return
        self.usage["prompt"] += u.prompt_tokens
        self.usage["completion"] += u.completion_tokens
        self.usage["total"] += u.total_tokens
        self.usage["calls"] += 1
        logger.debug(
            "TOKEN USAGE step: p=%s c=%s t=%s | session total=%s",
            u.prompt_tokens, u.completion_tokens, u.total_tokens, self.usage["total"],
        )

    def run(self, user_message: str, history: list = None):
        logger.info("\n👤 [%s] %s", self.name, _short_text(user_message, 200))
        logger.debug("USER (full):\n%s", user_message)

        if history is None:
            history = []
        if not history:
            history.append({"role": "system", "content": self.system_prompt})
            logger.debug("SYSTEM PROMPT [%s]:\n%s", self.name, self.system_prompt)

        history.append({"role": "user", "content": user_message})

        for iteration in range(self.max_iterations):
            logger.info("  [%d/%d]", iteration + 1, self.max_iterations)
            response = self.client.chat.completions.create(
                model=self.model_uri,
                messages=history,
                tools=self.tools_schema or None,
                tool_choice="auto" if self.tools_schema else None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            self._account(response)

            message = response.choices[0].message
            finish = response.choices[0].finish_reason
            logger.debug("finish_reason: %s", finish)

            if message.content and message.tool_calls:
                short = _short_text(message.content, 140)
                if short:
                    logger.info("    💭 %s", short)

            # пустой ответ
            if finish == "stop" and not message.tool_calls:
                content = message.content or ""
                if not content.strip():
                    logger.warning("⚠️ Пустой ответ, пинаю…")
                    history.append({"role": "assistant", "content": ""})
                    history.append({"role": "user", "content": self.empty_cont})
                    continue
                history.append({"role": "assistant", "content": content})
                return content, history

            # обрезан
            if finish == "length" and not message.tool_calls:
                logger.info("    ⚠️ Ответ обрезан, продолжаю…")
                history.append({"role": "assistant", "content": message.content or ""})
                history.append({"role": "user", "content": self.truncated_cont})
                continue

            # финал без tool_calls
            if not message.tool_calls:
                history.append({"role": "assistant", "content": message.content})
                return message.content, history

            # tool_calls
            history.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [tc.model_dump() for tc in message.tool_calls],
            })
            for tc in message.tool_calls:
                self._exec_tool(tc, history)

        logger.error("Превышено max_iterations (%d)", self.max_iterations)
        return f"❌ Превышено максимальное число итераций ({self.max_iterations})", history

    def _exec_tool(self, tool_call, history):
        func_name = tool_call.function.name
        try:
            func_args = json.loads(tool_call.function.arguments or "{}")
        except json.JSONDecodeError:
            func_args = {}

        logger.info("    🔧 %s(%s)", func_name, _short_args(func_args))
        logger.debug("TOOL CALL: %s args=%s", func_name, json.dumps(func_args, ensure_ascii=False))

        if func_name in self.router:
            try:
                result_text = str(self.router[func_name](**func_args))
            except Exception as e:
                logger.exception("Ошибка инструмента %s", func_name)
                result_text = f"❌ Ошибка выполнения: {e}"
        else:
            logger.error("Инструмент '%s' не найден", func_name)
            result_text = f"❌ Инструмент '{func_name}' не найден"

        status = "✓" if not result_text.startswith("❌") else "✗"
        logger.info("       %s %s | %d симв.", status, func_name, len(result_text))
        logger.debug("TOOL RESULT [%s] (%d chars):\n%s", func_name, len(result_text), result_text)

        history.append({"role": "tool", "tool_call_id": tool_call.id, "content": result_text})


# ============================================================
# Сборка: клиент, MCP, инструменты, системный промпт
# ============================================================
PROMPTS = load_prompts()
GENERATION = PROMPTS.get("generation", {})
GENERATION["continuation_prompts"] = PROMPTS.get("continuation_prompts", {})

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_MODEL = GENERATION.get("model", "yandexgpt/latest")
MODEL_URI = f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}"

client = OpenAI(
    api_key=YANDEX_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_FOLDER_ID,
)


def init_mcp_client():
    if not MCP_AVAILABLE:
        return None
    try:
        mcp = SyncMCPClient(url=os.getenv("TUTU_MCP_URL", "https://mcp.tutu.ru/mcp"))
        if mcp.initialize():
            logger.info("✅ MCP-клиент (Туту) подключён")
            return mcp
        logger.warning("⚠️ MCP-клиент не инициализирован")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации MCP: {e}")
    return None


mcp_client = init_mcp_client()
ALL_TOOLS = create_all_tools(client, model_name=MODEL_URI, mcp_client=mcp_client, mcp_mode="proxy")


def tutu_catalog() -> str:
    """Короткий каталог инструментов Туту для системного промпта (живой или fallback)."""
    if mcp_client:
        md = mcp_client.tools_catalog_markdown()
        if md and not md.startswith("_MCP"):
            return md
    return tutu_catalog_markdown_fallback()


def build_system_prompt(extra: str = "") -> str:
    base = PROMPTS.get("system_prompt", "")
    catalog = load_skills_catalog()
    tutu = tutu_catalog() if mcp_client else "_MCP-сервер Туту не подключён._"
    return (
        base
        + date_context_block()
        + "\n\n## Каталог доступных навыков\n"
        + "(Выбери по колонке «когда использовать» и загрузи через load_skill.)\n\n"
        + catalog
        + "\n\n## Каталог инструментов Туту (вызывай через `tutu_call`)\n"
        + "Вызов: `tutu_call(tool=\"search_avia\", args_json='{\"origin\":\"Москва\",...}')`\n\n"
        + tutu
        + (("\n\n" + extra) if extra else "")
    )


# ============================================================
# Публичный API: единый агент (обратная совместимость)
# ============================================================
_default_agent = None


def get_agent() -> Agent:
    global _default_agent
    if _default_agent is None:
        _default_agent = Agent(
            client=client,
            model_uri=MODEL_URI,
            system_prompt=build_system_prompt(),
            tool_functions=ALL_TOOLS,
            generation=GENERATION,
            name="tour-assistant",
        )
    return _default_agent


def chat_with_agent(user_message: str, conversation_history: list = None):
    """Обратная совместимость с v1.3 API."""
    agent = get_agent()
    return agent.run(user_message, conversation_history)


# ============================================================
# Хелпер для оркестратора: создать агента-исполнителя под навык
# ============================================================
def spawn_executor(skill_name: str, orchestrator_system_prompt: str, name: str = None) -> Agent:
    """Создаёт агента-исполнителя с ограниченным под навык набором инструментов
    и системным промптом, который написал оркестратор.

    Оркестратор отвечает за содержание orchestrator_system_prompt; сюда же
    подмешивается контекст даты и каталог Туту (если навык туристический).
    """
    tools = filter_tools_for_skill(ALL_TOOLS, skill_name)
    prompt = orchestrator_system_prompt + date_context_block()
    if any(getattr(t, "_tool_name", "") == "tutu_call" for t in tools):
        prompt += "\n\n## Каталог инструментов Туту (вызывай через `tutu_call`)\n\n" + tutu_catalog()
    return Agent(
        client=client, model_uri=MODEL_URI, system_prompt=prompt,
        tool_functions=tools, generation=GENERATION, name=name or f"executor:{skill_name}",
    )


# ============================================================
# Интерактивный режим
# ============================================================
def interactive_mode():
    print("=" * 60)
    print("🚀 Агент-туроператор (Яндекс AI Studio + Tutu MCP) запущен")
    print("=" * 60)
    print("Инструменты:")
    for f in ALL_TOOLS:
        if hasattr(f, "_tool_name"):
            print(f"  • {f._tool_name}")
    print("=" * 60)
    print(f"📄 Промпты: {PROMPTS_FILE}\n📄 Лог: {LOG_FILE}")
    print("Введите 'exit' для выхода. Пустой Enter — самопрезентация.\n")

    agent = get_agent()
    history = []
    self_intro = (PROMPTS.get("self_intro_prompt") or "").strip()

    while True:
        user_input = input("👤 Вы: ").strip()
        if user_input.lower() in ["exit", "quit", "выход"]:
            u = agent.usage
            print(f"👋 До свидания! Токенов за сессию: {u['total']} (prompt={u['prompt']}, completion={u['completion']}, вызовов={u['calls']})")
            break
        if not user_input:
            user_input = self_intro
            print(f"   (→ {_short_text(user_input, 80)})")
        response, history = agent.run(user_input, history)
        print(f"\n🤖 Агент:\n{response}\n")
        u = agent.usage
        print(f"   ⚙️ токены сессии: {u['total']} (Δ prompt={u['prompt']}, completion={u['completion']})\n")


if __name__ == "__main__":
    print("=" * 60)
    print(f"🚀 Новая сессия | лог: {LOG_FILE}")
    print("=" * 60)
    interactive_mode()
