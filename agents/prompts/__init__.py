"""
agents.prompts — работа с промптами агентов.

Экспортирует:
    PromptLoader — загрузчик и рендерер Jinja2-шаблонов промптов.
"""

from agents.prompts.prompt_loader import PromptLoader

__all__ = [
    "PromptLoader",
]