"""
Консольный интерфейс (async, мультиагентный).
Показывает эмодзи-«шапочки» для каждого специалиста, время ответа логируется.
Добавлена поддержка долгосрочной памяти через команды /я, /память, /забудь.
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Any, List
from config import get_settings
from agents.orchestrator import AsyncOrchestrator
from agents.specs import DEFAULT_TEAM
from client.session import Session
from client.memory import MemoryStore

memory = MemoryStore()
logger = logging.getLogger("travel_agent.cli")

_AGENT_EMOJIS = {spec.name: spec.emoji for spec in DEFAULT_TEAM}

def _emoji_for(agent_name: str) -> str:
    return _AGENT_EMOJIS.get(agent_name, "🤖")

def _tool_names(tool_calls: Any) -> List[str]:
    names: List[str] = []
    for tc in (tool_calls or []):
        if isinstance(tc, str):
            names.append(tc)
        elif isinstance(tc, dict):
            name = tc.get("tool") or tc.get("name")
            if not name and isinstance(tc.get("function"), dict):
                name = tc["function"].get("name")
            names.append(str(name) if name else "tool")
        else:
            name = getattr(tc, "name", None)
            names.append(str(name) if name else "tool")
    return names

async def async_chat_loop(settings) -> None:
    orchestrator = AsyncOrchestrator(DEFAULT_TEAM, settings=settings, memory=memory)
    session = Session()
    last_agent: str | None = None
    team_line = "  ".join(spec.label for spec in DEFAULT_TEAM)

    print("\n🚆 TUTU TRAVEL AGENT (Async Multi-Agent)")
    print(f"👥 Команда: {team_line}")
    print("💬 Напишите запрос. Команды: '/я <имя>', '/память', '/забудь', 'выход' / 'exit'.\n")
    
    try:
        while True:
            try:
                user_input = input("👤 Вы: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 До встречи!")
                break
            
            if not user_input:
                continue
            if user_input.lower() in {"выход", "exit", "quit", "q"}:
                print("\n👋 До встречи!")
                break
            
            if user_input.lower() == "/memory":
                import sqlite3
                from datetime import datetime
                try:
                    conn = sqlite3.connect("data/memory.db")
                    conn.row_factory = sqlite3.Row
                    alias = session.user_alias or "unknown"
                    cursor = conn.execute("""
                        SELECT content, created_at FROM memories m
                        JOIN users u ON u.id = m.user_id
                        WHERE u.alias = ?
                        ORDER BY m.created_at DESC LIMIT 5
                    """, (alias,))
                    rows = cursor.fetchall()
                    conn.close()
                    if rows:
                        print("\n🧠 Моя память о вас:")
                        for i, row in enumerate(rows, 1):
                            dt = datetime.fromtimestamp(row['created_at']).strftime("%H:%M")
                            print(f"  {i}. [{dt}] {row['content']}")
                    else:
                        print(f"\n🧠 Я пока ничего не запомнил о пользователе '{alias}'.")
                    print()
                    continue
                except Exception as e:
                    print(f"\n⚠️ Ошибка чтения памяти: {e}\n")
                    continue

            started = time.perf_counter()
            try:
                final_text, messages, tool_calls, agent_name = await orchestrator.run(
                    user_input, session.history, last_agent, user_alias=session.user_alias
                )
            except Exception as e:
                logger.exception("Ошибка при обработке запроса")
                print(f"\n⚠️ Упс, что-то пошло не так: {e}\n")
                continue
            
            elapsed = time.perf_counter() - started
            last_agent = agent_name
            session.messages = messages
            if tool_calls:
                session.record_tool_calls(tool_calls)
            
            emoji = _emoji_for(agent_name)
            # ИСПРАВЛЕНО: добавлен .strip() к final_text, чтобы убрать лишние переносы строк в начале ответа
            print(f"\n{emoji} Ответ:\n{final_text.strip()}\n")
            
            names = _tool_names(tool_calls)
            tools_used = ", ".join(names) if names else "—"
            logger.debug(f"[{agent_name}] ⏱ {elapsed:.1f}s  🔧 {tools_used}")
            
    finally:
        await orchestrator.close()

def main(api_type: str = "openai") -> int:
    settings = get_settings()
    try:
        asyncio.run(async_chat_loop(settings))
    except KeyboardInterrupt:
        print("\n👋 До встречи!")
    return 0
