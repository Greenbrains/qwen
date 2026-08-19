"""
Orchestrator — мультиагентный роутер.
Version: 5.3.0
Description: 
- Роутер выбирает навык (touragent, marketingskills, general)
- Для general используется модель yandex_model_general БЕЗ инструментов
- Для touragent/marketingskills используется yandex_model_agent С инструментами
- Дата передаётся в системный промпт только для touragent/marketingskills
"""
import logging
from typing import List

from agent.base import BaseAgent, UsageTracker
from agent.core.prompts.loader import PromptLoader
from agent.core.tools.agent_tools import load_skill


logger = logging.getLogger("agent.orchestrator")


class Orchestrator:
    def __init__(self, client, folder_id: str, mcp_client, registry, settings):
        self.client = client
        self.folder_id = folder_id
        self.mcp_client = mcp_client
        self.registry = registry
        self.settings = settings
        self.prompt_loader = PromptLoader()
        self.usage = UsageTracker()

    def route_and_execute(self, user_message: str, history: List[dict]) -> str:
        # ============== 1. РОУТИНГ ==============
        router_prompt = (
            "Ты роутер. Выбери навык из: touragent, marketingskills, general.\n"
            "- Если про путешествия/билеты/отели/трансферы/как добраться — touragent.\n"
            "- Если про маркетинг/SEO/копирайтинг/анализ конкурентов/презентации PPTX — marketingskills.\n"
            "- Иначе general (простые вопросы, фото, тексты без инструментов).\n"
            "Ответь ТОЛЬКО одним словом."
        )
        router = BaseAgent(
            client=self.client,
            model_uri=self.settings.get_model_uri(self.settings.yandex_model_router),
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
        if skill_name == "general":
            # === General: простой запрос без инструментов ===
            # Модель сама отвечает, дата не нужна
            sys_prompt = (
                "Ты вежливый ИИ-ассистент. Отвечай кратко и по делу на русском языке.\n"
                "У тебя нет доступа к инструментам — отвечай своими знаниями."
            )
            tools_schema = []
            tool_router = {}
            model_uri = self.settings.get_model_uri(self.settings.yandex_model_general)
        else:
            # === Touragent или Marketingskills: с инструментами и датой ===
            skill_instructions = load_skill(skill_name)
            skill_context = skill_instructions + (
                "\n\n> ⚠️ ВАЖНО: текст этого навыка УЖЕ встроен в системный промпт. "
                "НЕ вызывай load_skill с этим именем повторно."
            )

            tools_schema, tool_router = self.registry.get_tools_for_skill(skill_name)

            sys_prompt = self.prompt_loader.render_system_prompt(
                mcp_catalog_markdown=self.mcp_client.tools_catalog_markdown(),
                skill_context=skill_context,
            )
            model_uri = self.settings.get_model_uri(self.settings.yandex_model_agent)

        # ============== 3. ЗАПУСК ИСПОЛНИТЕЛЯ ==============
        executor = BaseAgent(
            client=self.client,
            model_uri=model_uri,
            system_prompt=sys_prompt,
            tools_schema=tools_schema,
            tool_router=tool_router,
            usage_tracker=self.usage,
            role_name="executor",
        )
        response = executor.run(user_message)

        logger.info(f"\n{self.usage.summary()}")
        return response
