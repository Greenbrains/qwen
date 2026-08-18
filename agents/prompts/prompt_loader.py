"""
Загрузчик системных промптов и каталога скиллов (чистый Python, без Jinja2).
Версия: v4.0 — упрощённая структура, скилы в формате Anthropic Agent Skills.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List

WEEKDAYS_RU = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

_DATE_HEADER = """📅 ТЕКУЩАЯ ДАТА
Сегодня: {current_date} ({current_weekday}), время {current_time}.
Текущий год: {current_year}.
Завтра: {tomorrow_date}; послезавтра: {day_after_tomorrow_date}; через неделю: {plus_week_date}.
Все даты поиска — не раньше {current_date} и только в {current_year} году."""

_SEPARATOR = "\n\n---\n\n"


class PromptLoader:
    """Загрузчик промптов и каталога скиллов."""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        self.prompts_dir = Path(__file__).resolve().parent if prompts_dir is None else Path(prompts_dir)
        self._cache: Dict[str, str] = {}

    def default_variables(self) -> Dict[str, Any]:
        """Возвращает переменные для подстановки даты."""
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
        """Разрешает путь к файлу промпта."""
        if not prompt_name.endswith(".md"):
            prompt_name = f"{prompt_name}.md"
        return self.prompts_dir / prompt_name

    def load_prompt(self, prompt_name: str, use_cache: bool = True) -> str:
        """Загружает промпт из файла."""
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
        """Загружает каталог скиллов из agents/skills/SKILLS_CATALOG.md."""
        skills_dir = self.prompts_dir.parent / "skills"
        catalog_path = skills_dir / "SKILLS_CATALOG.md"
        if catalog_path.exists():
            return catalog_path.read_text(encoding="utf-8")
        return ""

    def load_skill(self, skill_name: str) -> str:
        """
        Загружает текст навыка по имени.
        Если skill_name пуст — возвращает каталог скиллов.
        """
        if not skill_name or skill_name.strip() == "":
            return self.get_skills_catalog()
        
        skills_dir = self.prompts_dir.parent / "skills"
        skill_path = skills_dir / f"{skill_name.strip()}.md"
        
        if not skill_path.exists():
            return f"⚠️ Навык '{skill_name}' не найден. Доступные навыки см. в каталоге."
        
        return skill_path.read_text(encoding="utf-8")

    def compose(self, prompt_names: List[str], variables=None) -> str:
        """Композиция нескольких промптов с заголовком даты."""
        vars_ = self.default_variables()
        vars_.update(variables or {})
        parts = [_DATE_HEADER.format(**vars_)]
        parts += [self.load_prompt(name) for name in prompt_names]
        return _SEPARATOR.join(parts)

    def get_system_prompt(self, variables=None) -> str:
        """
        Возвращает минимальный системный промпт.
        В v4.0 все описания инструментов вынесены в скилы.
        """
        base_prompt = """## 🎯 Роль
Ты — профессиональный туристический ассистент.
Помогаешь планировать поездки: билеты (авиа, ж/д, автобусы, электрички), отели, мультимодальные маршруты.

## 🎯 Ключевые принципы
1. НИКОГДА не выдумывай цены, даты, наличие мест — используй только данные из MCP-инструментов.
2. Если инструмент не вернул данных — честно сообщи об этом.
3. Уточняющие вопросы задавай только при критической нехватке данных.
4. После поиска предлагай следующие шаги: детали тарифа, ссылка на бронирование, альтернативы, отель.

## 🌐 Язык
Отвечай на русском. Дружелюбный, профессиональный тон. Эмодзи — умеренно."""
        
        return _DATE_HEADER.format(**self.default_variables()) + "\n\n" + base_prompt

    def get_combined_prompt(self, variables: Optional[Dict[str, Any]] = None) -> str:
        """Устаревший метод, использует get_system_prompt."""
        return self.get_system_prompt(variables)

    def list_available_prompts(self) -> list:
        """Возвращает список доступных промптов."""
        if not self.prompts_dir.exists():
            return []
        return sorted(f.stem for f in self.prompts_dir.glob("*.md"))

    def clear_cache(self) -> None:
        """Очищает кэш промптов."""
        self._cache.clear()
