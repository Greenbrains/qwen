"""
orchestrator.py — Мультиагентный оркестратор (v2.4)

Роль: «менеджер». Принимает запрос, выбирает исполнителя, запускает его.
Своих предметных инструментов не имеет.

Ключевые оптимизации v2.4 (экономия токенов):
1. Трёхступенчатый роутинг «дёшево → дорого»:
     keyword  →  sticky (тот же агент)  →  LLM (последний резерв).
   LLM-вызов роутинга случается РЕДКО, а не на каждый запрос.
2. История хранится ОТДЕЛЬНО ПО КАЖДОМУ АГЕНТУ. Субагент видит только свой
   контекст (без чужих system-промптов) — меньше токенов, нет путаницы.
3. Агенты кэшируются и переиспользуются между ходами (не пересобираются).
4. Учёт токенов проброшен в каждого субагента (общий UsageTracker).
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from agent_builder import AsyncAgentBuilder
from usage import UsageTracker

if TYPE_CHECKING:
    from agent import Agent 

logger = logging.getLogger("agent.orchestrator")

# Быстрый бесплатный роутинг по ключевым словам: агент -> триггеры.
_KEYWORD_ROUTES = {
    "touragent": (
        "билет", "тур", "поезд", "жд", "ж/д", "ржд", "самол", "авиа", "рейс",
        "перелет", "перелёт", "отел", "гостиниц", "электрич", "автобус",
        "как добраться", "аэропорт", "вокзал", "заселен", "проживан", "сапсан",
    ),
    "marketingskills": (
        "маркетинг", "конкурент", "seo", "позиционир", "цел", "аудитор",
        "продвижен", "лендинг", "копирайт", "воронк", "оффер", "icp", "growth",
    ),
}

# Явные сигналы «переключи меня» — сбрасывают липкость (sticky).
_SWITCH_HINTS = ("вместо этого", "другой вопрос", "смени тему", "теперь про")


class AsyncOrchestrator:
    """Маршрутизатор запросов к специализированным агентам."""

    def __init__(
        self,
        builder: AsyncAgentBuilder,
        available_agents: Dict[str, Dict],
        usage: Optional[UsageTracker] = None,
    ):
        """
        Description: Инициализирует оркестратор.
        Input:
            - builder (AsyncAgentBuilder): фабрика агентов.
            - available_agents (Dict): конфигурация доступных агентов.
            - usage (UsageTracker): общий счётчик токенов.
        Output: None.
        """
        self.builder = builder
        self.agents_config = available_agents
        self.usage = usage or UsageTracker()

        self._last_agent: Optional[str] = None          # для sticky-роутинга
        self._agents: Dict[str, "Agent"] = {}           # кэш собранных агентов
        self._histories: Dict[str, List[Dict]] = {}     # история ПО КАЖДОМУ агенту

    # ------------------------------------------------------------------
    # Роутинг: дёшево → дорого
    # ------------------------------------------------------------------
    def _keyword_route(self, text: str) -> Optional[str]:
        """Быстрый бесплатный роутинг по ключевым словам."""
        low = text.lower()
        for agent_name, keywords in _KEYWORD_ROUTES.items():
            if agent_name in self.agents_config and any(kw in low for kw in keywords):
                return agent_name
        return None

    def _is_followup(self, text: str) -> bool:
        """Похоже ли на продолжение текущей темы (короткая уточняющая реплика)?"""
        low = text.lower()
        if any(h in low for h in _SWITCH_HINTS):
            return False
        # Короткие реплики без явных ключевых слов трактуем как уточнение.
        return len(text.split()) <= 12

    async def _llm_route(self, user_input: str) -> str:
        """Резервный LLM-роутинг (дорогой) — только когда дешёвые не сработали."""
        agents_list = "\n".join(f"- {n}: {c['description']}" for n, c in self.agents_config.items())
        valid = ", ".join(self.agents_config.keys())
        prompt = (
            "Ты — маршрутизатор. Выбери ОДНОГО специалиста для запроса.\n"
            f"Специалисты:\n{agents_list}\n"
            f"Ответь СТРОГО одним словом из: {valid}.\n"
            f"Запрос: {user_input}\nСпециалист:"
        )
        try:
            client = self.builder.get_llm_client()
            resp = await client.chat.completions.create(
                model=self.builder.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=8,
            )
            self.usage.record("router", getattr(resp, "usage", None))
            ans = (resp.choices[0].message.content or "").strip().lower()
            for name in self.agents_config:
                if name in ans:
                    return name
        except Exception as e:
            logger.error("Ошибка LLM-роутинга: %s", e)
        return "general"

    async def _route(self, user_input: str) -> str:
        """Трёхступенчатый выбор агента: keyword → sticky → LLM."""
        # 1) Ключевые слова — бесплатно и точно.
        kw = self._keyword_route(user_input)
        if kw:
            if kw != self._last_agent:
                logger.info("🧭 keyword-роутинг → %s", kw)
            return kw

        # 2) Липкость: продолжаем с тем же агентом, если это уточнение.
        if self._last_agent and self._is_followup(user_input):
            logger.info("🧭 sticky-роутинг → %s (продолжение темы, LLM не вызываем)", self._last_agent)
            return self._last_agent

        # 3) Дорогой резерв — LLM.
        chosen = await self._llm_route(user_input)
        logger.info("🧭 LLM-роутинг → %s", chosen)
        return chosen

    # ------------------------------------------------------------------
    # Ленивое получение/сборка агента (с кэшированием)
    # ------------------------------------------------------------------
    async def _get_agent(self, agent_name: str) -> "Agent":
        """Возвращает готового агента из кэша либо собирает его один раз."""
        if agent_name in self._agents:
            return self._agents[agent_name]

        config = self.agents_config.get(agent_name, self.agents_config.get("general", {}))
        mcp_needed = {mcp: "mock_url" for mcp in config.get("mcp", [])}
        agent = await self.builder.build(
            agent_name=agent_name,
            skill_name=config.get("skill", "general"),
            custom_system_prompt=config.get("system_prompt"),
            extra_tools=config.get("extra_tools", []),
            mcp_endpoints=mcp_needed,
            usage=self.usage,
        )
        self._agents[agent_name] = agent
        return agent

    # ------------------------------------------------------------------
    # Главный вход
    # ------------------------------------------------------------------
    async def run(self, user_input: str) -> Tuple[str, str]:
        """
        Description: Маршрутизирует запрос, запускает агента, копит его историю.
        Input:
            - user_input (str): запрос пользователя.
        Output:
            - Tuple[str, str]: ответ агента и имя выбранного агента.
        """
        agent_name = await self._route(user_input)
        agent = await self._get_agent(agent_name)

        # История ТОЛЬКО этого агента — чужие system-промпты не подмешиваются.
        history = self._histories.get(agent_name)
        response_text, updated = await agent.run(user_input, history=history)

        self._histories[agent_name] = updated
        self._last_agent = agent_name

        # Токены за этот ход — в консоль (как любил одиночный агент).
        logger.info(self.usage.turn_line(agent_name))

        return response_text, agent_name

    def clear(self) -> None:
        """Сбрасывает историю всех агентов и липкость (команда 'clear')."""
        self._histories.clear()
        self._last_agent = None

    async def close(self) -> None:
        """Освобождает ресурсы через builder."""
        await self.builder.close()