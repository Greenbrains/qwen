"""
Пакет агентов.
Реэкспорт публичных классов для удобных импортов вида:
    from agents import AsyncAgentBuilder, AsyncOrchestrator
"""
from __future__ import annotations

from agents.specs import AgentSpec, DEFAULT_TEAM
from agents.builder import AsyncAgentBuilder
from agents.orchestrator import AsyncOrchestrator

__all__ = [
    "AgentSpec",
    "DEFAULT_TEAM",
    "AsyncAgentBuilder",
    "AsyncOrchestrator",
]