"""
Мультиагентный оркестратор: роутер + специалисты.
Роутер — один лёгкий LLM-вызов, выбирает специалиста по описаниям и каталогу
скиллов. Специалисты создаются лениво при первом обращении. История общая.

Добавлено (пункт 1.3):
- Компактизация истории после каждого хода (compact_messages).
- Сохранение маркеров в долгосрочную память (MemoryStore), если пользователь
  идентифицирован (user_alias).

Добавлено (v3.4 — Tool Hinting):
- Роутер возвращает {"agent": ..., "suggested_tool": ...}.
- Оркестратор вставляет hint-сообщение перед user-сообщением, направляя
  агента к конкретному инструменту. Hint удаляется из истории после ответа,
  чтобы не накапливаться.
"""

from __future__ import annotations
import logging
import re
from typing import Dict, List, Optional, Tuple
import openai
from config import get_settings
from agents.builder import AsyncAgentBuilder
from agents.specs import AgentSpec
from client.openai_agent import AsyncOpenAIAgent
from client.session import compact_messages
from client.memory import MemoryStore

logger = logging.getLogger("travel_agent.orchestrator")

_KEYWORD_ROUTES: List[Tuple[str, Tuple[str, ...]]] = [
    ("rail", ("электричк", "поезд", "жд", "ж/д", "ржд", "плацкарт", "купе", "сапсан", "ласточк", "вокзал", "пригород", "сидяч")),
    ("avia", ("самол", "авиа", "рейс", "перелет", "перелёт", "аэропорт", "лоукостер", "чартер", "стыковочн")),
    ("hotels", ("отел", "гостиниц", "апартамент", "хостел", "заселен", "заезд", "проживан", "где остановиться", "снять жиль", "номер на")),
    ("consultant", ("маршрут", "пересадк", "план", "стыковк", "поезд+самол", "виза", "составной", "как добраться", "добраться до" )),
]

_AVIA_DESTINATIONS: Tuple[str, ...] = (
    "анталь", "стамбул", "дубай", "ереван", "тбилиси", "баку", "стамбу", "хургад", "шарм", "пхукет", "бангкок", "гоа", "мальдив", "куала", "бали", "денпасар", "париж", "рим", "милан", "барселон", "мадрид", "лондон", "прага", "белград", "минск", "алматы", "астан", "ташкент", "бишкек", "тель-авив", "кипр", "ларнак", "анкар", "измир", "каир",
)
_TICKET_WORDS: Tuple[str, ...] = ("билет", "лететь", "долететь", "улетет")

class AsyncOrchestrator:
    def __init__(self, specs: List[AgentSpec], settings=None, memory: Optional[MemoryStore] = None):
        self._settings = settings or get_settings()
        self._factory = AsyncAgentBuilder(settings=self._settings)
        self._specs: Dict[str, AgentSpec] = {s.name.strip(): s for s in specs}
        self._agents: Dict[str, AsyncOpenAIAgent] = {}
        self._router_client: Optional[openai.AsyncOpenAI] = None
        self._memory = memory

    @property
    def team(self) -> List[str]:
        return list(self._specs.keys())

    def _get_router_client(self) -> openai.AsyncOpenAI:
        if self._router_client is None:
            self._router_client = openai.AsyncOpenAI(
                api_key=self._settings.api_key,
                base_url=self._settings.yandex_base_url,
            )
        return self._router_client

    async def _get_agent(self, name: str) -> AsyncOpenAIAgent:
        if name not in self._agents:
            logger.info(f"🏗️ Создаю агента [{name}]")
            self._agents[name] = await self._factory.build(self._specs[name], logger=logger)
        return self._agents[name]

    def _keyword_route(self, user_input: str) -> Optional[str]:
        text = user_input.lower()
        for name, keywords in _KEYWORD_ROUTES:
            if name not in self._specs:
                continue
            if any(kw in text for kw in keywords):
                return name
        if "avia" in self._specs:
            has_ticket = any(w in text for w in _TICKET_WORDS)
            has_dest = any(d in text for d in _AVIA_DESTINATIONS)
            if has_dest and (has_ticket or "москва" in text or "→" in text or "-" in text):
                return "avia"
        return None

    def _match_name(self, text: str) -> Optional[str]:
        low = text.lower()
        for name in self._specs:
            if re.search(rf"\b{re.escape(name.lower())}\b", low):
                return name
        return None

    async def _route(self, user_input: str, last_agent: Optional[str]) -> Dict[str, Optional[str]]:
        kw = self._keyword_route(user_input)
        if kw:
            logger.info(f"🔑 Роутинг по ключевым словам → {kw}")
            return {"agent": kw, "suggested_tool": None}

        agents_list = "\n".join(f"- {s.name}: {s.description}" for s in self._specs.values())
        valid_names = ", ".join(self._specs.keys())
        context_hint = f"Предыдущий специалист: {last_agent}. Учитывай его ТОЛЬКО если запрос — уточнение к прошлой теме. Если тема сменилась — выбирай заново.\n" if last_agent else ""

        prompt = (
            "Ты — маршрутизатор запросов в тревел-сервисе. Определи ОДНОГО специалиста.\n\n"
            f"Доступные специалисты:\n{agents_list}\n\n"
            "Правила:\n"
            "- Поезда, электрички, РЖД, плацкарт, купе → rail\n"
            "- Самолёты, авиабилеты, рейсы, аэропорты, зарубежные/курортные направления → avia\n"
            "- Отели, гостиницы, апартаменты, проживание → hotels\n"
            "- Сложные маршруты с пересадками, визы, справки → consultant\n"
            "- Приветствия и общее → general\n\n"
            f"{context_hint}"
            f"Ответь СТРОГО одним словом из списка: {valid_names}.\n"
            f"Запрос: {user_input}\n"
            "Специалист:"
        )
        try:
            client = self._get_router_client()
            resp = await client.chat.completions.create(
                model=self._settings.composite_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=8,
            )
            ans = (resp.choices[0].message.content or "").strip().lower()
            logger.info(f"🧠 LLM-роутер ответил: {ans!r}")
            matched = self._match_name(ans)
            if matched:
                return {"agent": matched, "suggested_tool": None}
            for name in self._specs:
                if name in ans:
                    return {"agent": name, "suggested_tool": None}
        except Exception as e:
            logger.warning(f"Router error: {e}")

        logger.info("↩️ Фолбэк роутера → general")
        return {"agent": "general" if "general" in self._specs else next(iter(self._specs)), "suggested_tool": None}

    @staticmethod
    def _make_hint_message(tool_name: str) -> Dict[str, str]:
        # ВАЖНО: Используем роль "user", а не "system", чтобы не нарушать строгое правило API 
        # "System message must be at the beginning". LLM отлично понимает инструкции в роли user.
        return {
            "role": "user",
            "content": (
                f"⚠️ ВАЖНАЯ ПОДСКАЗКА МАРШРУТИЗАТОРА: "
                f"Для этого запроса оптимально использовать инструмент `{tool_name}`. "
                f"Проверь наличие всех обязательных.args. Перед поиском ОБЯЗАТЕЛЬНО вызови соответствующий get_*_instructions."
            ),
        }

    @staticmethod
    def _strip_hints(messages: List[Dict]) -> List[Dict]:
        """Убирает hint-сообщения из истории, чтобы они не копились."""
        return [
            m for m in messages
            if not (
                m.get("role") == "user"
                and str(m.get("content", "")).startswith("⚠️ ВАЖНАЯ ПОДСКАЗКА МАРШРУТИЗАТОРА:")
            )
        ]

    async def run(self, user_input: str, history: list, last_agent: Optional[str] = None, user_alias: Optional[str] = None) -> Tuple[str, list, list, str]:
        route_info = await self._route(user_input, last_agent)
        name = route_info["agent"]
        suggested_tool = route_info.get("suggested_tool")

        logger.info(f"🧭 Роутер выбрал: {name}" + (f" (tool: {suggested_tool})" if suggested_tool else ""))
        agent = await self._get_agent(name)

        prepared_history = list(history)
        if suggested_tool:
            prepared_history.append(self._make_hint_message(suggested_tool))

        text, msgs, tools = await agent.run(user_input, prepared_history)

        # Очищаем историю от подсказок перед сохранением
        msgs = self._strip_hints(msgs)

        compacted, markers = compact_messages(msgs, keep_last_turns=2)

        if markers and self._memory and user_alias:
            for m in markers:
                self._memory.add_marker(user_alias, m)
            logger.debug(f"💾 Сохранено {len(markers)} маркеров для [{user_alias}]")

        return text, compacted, tools, name

    async def close(self) -> None:
        if self._router_client is not None:
            await self._router_client.close()
            self._router_client = None
        await self._factory.close()
        if self._memory:
            self._memory.close()