"""Декларации агентов-специалистов. Версия: v4.0"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AgentSpec:
    """Спецификация агента-специалиста."""
    name: str
    description: str = ""
    emoji: str = "🤖"
    title: str = ""
    model: Optional[str] = None  # Модель YandexGPT (например, "yandexgpt/latest")
    skill: str = "touragent"  # Имя скилла из каталога
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


# Модели YandexGPT из каталога: https://aistudio.yandex.ru/docs/ru/ai-studio/concepts/generation/models.html
# - yandexgpt/latest — базовая модель общего назначения
# - yandexgpt-lite/latest — лёгкая модель для простых задач (роутинг)
# - ruYmZ/latest — мультимодальная (текст + изображения)

DEFAULT_TEAM: List[AgentSpec] = [
    AgentSpec(
        name="touragent",
        emoji="🧳",
        title="Турагент",
        description="Подбор путешествий: авиа/жд/автобусы/электрички, отели, трансферы, мультимодальные маршруты",
        skill="touragent",
        model="yandexgpt/latest",  # Мощная модель для специалистов
    ),
    AgentSpec(
        name="general",
        emoji="🤖",
        title="Ассистент",
        description="Общие, приветственные и смешанные запросы",
        skill="touragent",  # Использует тот же скилл
        model="yandexgpt/latest",
    ),
]