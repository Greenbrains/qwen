# ============================================================
# orchestrator.py — Мультиагентный оркестратор (v2.3)
#
# Управляет историей, маршрутизацией, оценкой результатов и жизненным циклом субагентов.
# Роль: принять запрос пользователя, декомпозировать его, выбрать навык(и),
# СГЕНЕРИРОВАТЬ системный промпт для агента-исполнителя и запустить его.
# Исполнители имеют СВОИ скиллы (ограниченный набор инструментов из
# SKILL_TOOLSETS) — оркестратор лишь диктует им инструкцию (system prompt).
#
# Оркестратор сам инструментов предметной области не имеет — он «менеджер».
# ============================================================

from __future__ import annotations
import logging
import re
from typing import Dict, List, Optional, Tuple

from agent_builder import AsyncAgentBuilder

logger = logging.getLogger("agent.orchestrator")

# Простая эвристика для быстрого роутинга без затрат на LLM
_KEYWORD_ROUTES = {
    "rail": ("электрич", "поезд", "жд", "ж/д", "ржд", "плацкарт", "купе", "сапсан", "ласточк", "вокзал"),
    "avia": ("самол", "авиа", "рейс", "перелет", "перелёт", "аэропорт", "лоукостер", "чартер"),
    "hotels": ("отел", "гостиниц", "апартамент", "хостел", "заселен", "заезд", "проживан"),
    "web": ("найди в интернет", "поиск", "актуальная информация", "новости"),
}


class AsyncOrchestrator:
    """
    Manager class that routes user requests to the most appropriate specialized agent.
    """
    def __init__(self, builder: AsyncAgentBuilder, available_agents: Dict[str, Dict]):
        """
        Description: Initializes the Orchestrator with a builder and agent configurations.
        Input data:
            - builder (AsyncAgentBuilder): The factory for creating agent instances.
            - available_agents (Dict[str, Dict]): Configuration dictionary of available agents.
        Output: None (Initializes instance attributes).
        """
        self.builder = builder
        self.agents_config = available_agents
        self.history: List[Dict] = []

    def _keyword_route(self, user_input: str) -> Optional[str]:
        """
        Description: Performs fast, rule-based routing using keyword matching.
        Input data:
            - user_input (str): The raw user query.
        Output: Optional[str]: The matched agent name, or None if no match.
        """
        text = user_input.lower()
        for agent_name, keywords in _KEYWORD_ROUTES.items():
            if agent_name in self.agents_config and any(kw in text for kw in keywords):
                return agent_name
        return None

    async def _llm_route(self, user_input: str, last_agent: Optional[str]) -> str:
        """
        Description: Fallback LLM-based routing for complex or ambiguous queries.
        Input data:
            - user_input (str): The raw user query.
            - last_agent (Optional[str]): The agent used in the previous turn (for context).
        Output: str: The selected agent name (defaults to 'general' on failure).
        """
        agents_list = "\n".join(f"- {name}: {cfg['description']}" for name, cfg in self.agents_config.items())
        valid_names = ", ".join(self.agents_config.keys())
        
        prompt = (
            f"Ты — маршрутизатор. Выбери ОДНОГО специалиста из списка для запроса пользователя.\n"
            f"Специалисты:\n{agents_list}\n"
            f"Правила: отвечай СТРОГО одним словом из: {valid_names}.\n"
            f"Запрос: {user_input}\n"
            f"Специалист:"
        )
        
        try:
            client = self.builder.get_llm_client()
            resp = await client.chat.completions.create(
                model=self.builder.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10,
            )
            ans = (resp.choices[0].message.content or "").strip().lower()
            for name in self.agents_config:
                if name in ans:
                    return name
        except Exception as e:
            logger.error(f"Ошибка LLM-роутинга: {e}")
            
        return "general"

    async def run(self, user_input: str) -> Tuple[str, List[Dict]]:
        """
        Description: Main execution loop: routes request, builds agent, executes, and updates history.
        Input data:
            - user_input (str): The user's query.
        Output: Tuple[str, List[Dict]]: The agent's response and the updated global history.
        """
        self.history.append({"role": "user", "content": user_input})
        
        # 1. Маршрутизация
        last_agent = self.history[-3]["role"] if len(self.history) >= 3 and self.history[-3]["role"] != "system" else None
        agent_name = self._keyword_route(user_input) or await self._llm_route(user_input, last_agent)
        config = self.agents_config.get(agent_name, self.agents_config.get("general", {}))
        
        logger.info(f"🧭 Оркестратор выбрал агента: {agent_name}")
        
        # 2. Сборка специализированного агента "на лету"
        mcp_needed = {mcp: "mock_url" for mcp in config.get("mcp", [])} 
        sub_agent = await self.builder.build(
            skill_name=config.get("skill", "general"),
            custom_system_prompt=config.get("system_prompt"),
            extra_tools=config.get("extra_tools", []),
            mcp_endpoints=mcp_needed,
        )
        
        # 3. Выполнение задачи субагентом
        response_text, updated_history = await sub_agent.run(user_input, history=list(self.history))
        
        # 4. Обновление глобальной истории
        self.history = updated_history
        
        # Простая эвристика оценки: если агент просит уточнения, возвращаем управление пользователю
        if "уточни" in response_text.lower() or "не хватает" in response_text.lower():
            logger.info("🔄 Субагент запросил уточнение. Возврат управления пользователю.")
            
        return response_text, self.history

    async def close(self):
        """
        Description: Delegates resource cleanup to the underlying builder.
        Input data: None.
        Output: None.
        """
        await self.builder.close()