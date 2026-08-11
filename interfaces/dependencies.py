"""DI для FastAPI (Асинхронный)."""
from __future__ import annotations

import inspect
import logging

import aiohttp

from client.session import SessionStore
from config import get_settings
from agents.orchestrator import AsyncOrchestrator
from agents.specs import DEFAULT_TEAM

logger = logging.getLogger("travel_agent.dependencies")


class AppDependencies:
    def __init__(self):
        self.settings = get_settings()
        self.session_store = SessionStore()
        self.http_session: aiohttp.ClientSession = None
        self.orchestrator: AsyncOrchestrator = None
        # Эти два атрибута ждут websocket.py (/ws и /ws/voice)
        self.agent = None
        self.mcp_client = None

    async def startup(self) -> None:
        self.settings.validate_llm()
        self.http_session = aiohttp.ClientSession()
        self.orchestrator = AsyncOrchestrator(specs=DEFAULT_TEAM, settings=self.settings)

        # Достаём general-агента + его MCP-клиент для WebSocket/голоса
        try:
            get_agent = getattr(self.orchestrator, "_get_agent", None)
            if callable(get_agent):
                agent_or_coro = get_agent("general")
                self.agent = (
                    await agent_or_coro if inspect.iscoroutine(agent_or_coro) else agent_or_coro
                )
                self.mcp_client = (
                    getattr(self.agent, "mcp", None)
                    or getattr(self.agent, "mcp_client", None)
                    or getattr(self.agent, "_mcp", None)
                )
                logger.info(
                    "Agent for WS ready, mcp_client=%s",
                    "OK" if self.mcp_client else "MISSING",
                )
        except Exception as e:
            logger.warning("Не удалось получить агента/MCP из оркестратора: %s", e)

        logger.info("FastAPI dependencies ready")

    async def shutdown(self) -> None:
        if self.orchestrator:
            await self.orchestrator.close()
        if self.http_session:
            await self.http_session.close()


app_dependencies = AppDependencies()


def get_dependencies() -> AppDependencies:
    return app_dependencies