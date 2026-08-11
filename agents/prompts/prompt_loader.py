"""
Загрузчик системных промптов (чистый Python, без Jinja2).
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List

WEEKDAYS_RU = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

# ИСПРАВЛЕНО: убран начальный перенос строки \n после """
_DATE_HEADER = """📅 ТЕКУЩАЯ ДАТА
Сегодня: {current_date} ({current_weekday}), время {current_time}.
Текущий год: {current_year}.
Завтра: {tomorrow_date}; послезавтра: {day_after_tomorrow_date}; через неделю: {plus_week_date}.
Все даты поиска — не раньше {current_date} и только в {current_year} году."""

_SEPARATOR = "\n\n---\n\n"

class PromptLoader:
    def __init__(self, prompts_dir: Optional[str] = None):
        self.prompts_dir = Path(__file__).resolve().parent if prompts_dir is None else Path(prompts_dir)
        self._cache: Dict[str, str] = {}

    def default_variables(self) -> Dict[str, Any]:
        now = datetime.now()
        return {
            "current_date": now.strftime("%Y-%m-%d"),
            "current_time": now.strftime("%H:%M"),
            "current_datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "current_weekday": WEEKDAYS_RU[now.weekday()],
            "current_year": now.year,
            "tomorrow_date": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
            "day_after_tomorrow_date": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
            "plus_week_date": (now + timedelta(days=7)).strftime("%Y-%m-%d"),
        }

    def _resolve_path(self, prompt_name: str) -> Path:
        if not prompt_name.endswith(".md"):
            prompt_name = f"{prompt_name}.md"
        return self.prompts_dir / prompt_name

    def load_prompt(self, prompt_name: str, use_cache: bool = True) -> str:
        path = self._resolve_path(prompt_name)
        key = str(path)
        if use_cache and key in self._cache:
            return self._cache[key]
        if not path.exists():
            raise FileNotFoundError(f"Промпт не найден: {path}")
        content = path.read_text(encoding="utf-8").strip()
        if use_cache:
            self._cache[key] = content
        return content

    def get_skills_catalog(self) -> str:
        skills_dir = self.prompts_dir.parent / "skills"
        catalog_path = skills_dir / "SKILLS_CATALOG.md"
        if catalog_path.exists():
            return catalog_path.read_text(encoding="utf-8")
        return ""

    def compose(self, prompt_names: List[str], variables=None) -> str:
        vars_ = self.default_variables()
        vars_.update(variables or {})
        parts = [_DATE_HEADER.format(**vars_)]
        parts += [self.load_prompt(name) for name in prompt_names]
        return _SEPARATOR.join(parts)

    def get_system_prompt(self, variables=None) -> str:
        return self.compose(["travel_assistant", "mcp_instructions", "mcp_tools_rules"], variables)

    def get_combined_prompt(self, variables: Optional[Dict[str, Any]] = None) -> str:
        return self.get_system_prompt(variables)

    def get_travel_assistant_prompt(self) -> str:
        return self.load_prompt("travel_assistant")

    def get_mcp_instructions_prompt(self) -> str:
        return self.load_prompt("mcp_instructions")

    def get_mcp_tools_rules_prompt(self) -> str:
        return self.load_prompt("mcp_tools_rules")

    def list_available_prompts(self) -> list:
        if not self.prompts_dir.exists():
            return []
        return sorted(f.stem for f in self.prompts_dir.glob("*.md"))

    def clear_cache(self) -> None:
        self._cache.clear()