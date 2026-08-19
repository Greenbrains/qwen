"""
Orchestrator — мультиагентный роутер.
Version: 5.1.0
Description: Определяет навык по запросу и спавнит исполнителя с нужным контекстом.
"""
import logging
from typing import List

from agent.base import BaseAgent, UsageTracker
from agent.core.prompts.loader import PromptLoader
from agent.core.tools.agent_tools import load_skill


logger = logging.getLogger("agent.orchestrator")


class Orchestrator:
    """Роутер + спавнер исполнителей."""

    def __init__(self, client, folder_id: str, mcp_client, registry, settings):
        self.client = client
        self.folder_id = folder_id
        self.mcp_client = mcp_client
        self.registry = registry
        self.settings = settings
        self.prompt_loader = PromptLoader()
        # Общий трекер токенов для всей сессии
        self.usage = UsageTracker()

    def route_and_execute(self, user_message: str, history: List[dict]) -> str:
        # ============== 1. РОУТИНГ ==============
        router_prompt = (
            "Ты роутер. Выбери навык из: touragent, marketingskills, general. "
            "Если про путешествия/билеты/отели — touragent. "
            "Если про маркетинг/SEO/копирайтинг — marketingskills. "
            "Иначе general. Ответь ТОЛЬКО одним словом."
        )
        router = BaseAgent(
            client=self.client,
            folder_id=self.folder_id,
            model=self.settings.yandex_model_router,
            system_prompt=router_prompt,
            tools_schema=[],
            tool_router={},
            usage_tracker=self.usage,
            role_name="router",
        )
        skill_name = router.run(user_message, max_iterations=2).strip().lower()
        if skill_name not in ("touragent", "marketingskills", "general"):
            skill_name = "general"
        logger.info(f"🧭 Оркестратор выбрал навык: {skill_name}")

        # ============== 2. ПОДГОТОВКА ИСПОЛНИТЕЛЯ ==============
        skill_instructions = load_skill(skill_name)
        tools_schema, tool_router = self.registry.get_tools_for_skill(skill_name)

        sys_prompt = self.prompt_loader.render_system_prompt(
            mcp_catalog_markdown=self.mcp_client.tools_catalog_markdown(),
            skill_context=skill_instructions,
        )

        # ============== 3. ЗАПУСК ИСПОЛНИТЕЛЯ ==============
        executor = BaseAgent(
            client=self.client,
            folder_id=self.folder_id,
            model=self.settings.yandex_model_agent,
            system_prompt=sys_prompt,
            tools_schema=tools_schema,
            tool_router=tool_router,
            usage_tracker=self.usage,
            role_name="executor",
        )
        response = executor.run(user_message, history=history)

        # Выводим сводку по сессии
        logger.info(f"\n{self.usage.summary()}")
        return response