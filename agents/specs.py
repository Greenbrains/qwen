"""Декларации агентов-специалистов."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AgentSpec:
    name: str
    description: str = ""
    emoji: str = "🤖"           
    title: str = ""            
    model: Optional[str] = None
    skill: str = "full"
    extra_tools: List[str] = field(default_factory=list)
    api_type: str = "openai"
    prompt_id: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4096
    max_iterations: int = 12

    @property
    def label(self) -> str:
        """Готовая подпись вида '🚆 Ж/Д эксперт'."""
        return f"{self.emoji} {self.title or self.name}"


DEFAULT_TEAM: List[AgentSpec] = [
    AgentSpec(
        name="rail",
        emoji="🚆",
        title="Ж/Д эксперт",
        description="Поезда дальнего следования и электрички, выбор мест, багаж",
        skill="rail",
    ),
    AgentSpec(
        name="avia",
        emoji="✈️",
        title="Авиа-эксперт",
        description="Авиабилеты: рейсы, тарифы, багаж, стыковки",
        skill="avia",
    ),
    AgentSpec(
        name="hotels",
        emoji="🏨",
        title="Эксперт по отелям",
        description="Отели, апартаменты, хостелы: подбор по датам и бюджету",
        skill="hotels",
    ),
    AgentSpec(
        name="consultant",
        emoji="🧭",
        title="Консультант по маршрутам",
        description="Сложные мультимодальные маршруты (поезд+самолёт), пересадки, визы, справки",
        skill="consultant",
    ),
    AgentSpec(
        name="general",
        emoji="🤖",
        title="Ассистент",
        description="Общие, приветственные и смешанные запросы",
        skill="full",
    ),
]