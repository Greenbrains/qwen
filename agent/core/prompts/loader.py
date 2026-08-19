"""
Загрузчик системных промптов с инжекцией даты.
Version: 5.2.1
Description: Читает .agents/prompts/system.yaml, собирает финальный системный промпт
             с текущей датой, годом, относительными датами (завтра/через неделю)
             и каталогом MCP-инструментов.
"""
import yaml
from datetime import datetime, timedelta
from pathlib import Path


WEEKDAYS_RU = [
    "понедельник", "вторник", "среда", "четверг",
    "пятница", "суббота", "воскресенье",
]

# Жёсткий блок с датой — вставляется в системный промпт КАЖДОМУ агенту
_DATE_BLOCK_TEMPLATE = """
## ⏰ ТЕКУЩАЯ ДАТА (ОБЯЗАТЕЛЬНО К УЧЁТУ)
Сегодня: **{date}** ({weekday}) — **{year} год**.
Завтра: {tomorrow}. Послезавтра: {day_after}. Через неделю: {plus_week}.
Ближайшие выходные: {next_sat}–{next_sun}.

**КРИТИЧЕСКИ ВАЖНО:**
- Все даты поиска билетов, отелей и туров — не раньше **{date}**.
- Все поиски происходят в **{year}** году. Не предлагай даты в прошлом.
- Если пользователь говорит «завтра» → это {tomorrow}.
- Если «на следующей неделе» → считай относительно {date}.
- Если «на выходных» / «в субботу» → ближайшие {next_sat}.
- Если «в августе» без года → это август {year}.
- **Никогда не спрашивай у пользователя год**, если в запросе его нет — подразумевай {year}.
"""


class PromptLoader:
    def __init__(self, prompts_dir: str | Path = ".agents/prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._config = None

    def _load_config(self) -> dict:
        if self._config is not None:
            return self._config
        path = self.prompts_dir / "system.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Файл промптов не найден: {path}")
        with open(path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}
        return self._config

    def _build_date_block(self) -> str:
        """Строит блок с текущей датой и относительными датами."""
        now = datetime.now()
        today = now.date()
        weekday_idx = today.weekday()

        # Ближайшие выходные
        days_to_sat = (5 - weekday_idx) % 7
        if days_to_sat == 0:
            days_to_sat = 7  # если сегодня суббота — берём следующую
        next_sat = today + timedelta(days=days_to_sat)
        next_sun = next_sat + timedelta(days=1)

        return _DATE_BLOCK_TEMPLATE.format(
            date=today.strftime("%Y-%m-%d"),
            year=today.year,
            weekday=WEEKDAYS_RU[weekday_idx],
            tomorrow=(today + timedelta(days=1)).strftime("%Y-%m-%d"),
            day_after=(today + timedelta(days=2)).strftime("%Y-%m-%d"),
            plus_week=(today + timedelta(days=7)).strftime("%Y-%m-%d"),
            next_sat=next_sat.strftime("%Y-%m-%d"),
            next_sun=next_sun.strftime("%Y-%m-%d"),
        )

    def render_system_prompt(
        self,
        mcp_catalog_markdown: str = "",
        skill_context: str = "",
    ) -> str:
        """Собирает финальный системный промпт."""
        config = self._load_config()
        base = (config.get("system_prompt") or "").strip()
        date_block = self._build_date_block()

        mcp_section = ""
        if mcp_catalog_markdown:
            mcp_section = (
                "\n\n## Каталог инструментов Туту (MCP)\n"
                "Точные имена инструментов и их поля (required/optional) — в таблице ниже. "
                "Используй **только** эти имена и поля в `tutu_call`.\n\n"
                f"{mcp_catalog_markdown}"
            )

        skill_section = ""
        if skill_context:
            skill_section = (
                "\n\n## Инструкция активного навыка\n"
                "Следуй этому рабочему процессу буквально.\n\n"
                f"{skill_context}"
            )

        return (
            f"{base}\n"
            f"{date_block}"
            f"{mcp_section}"
            f"{skill_section}"
        )

    # ---- Вспомогательные методы (на будущее) ----
    def get_base_prompt(self) -> str:
        return (self._load_config().get("system_prompt") or "").strip()

    def get_self_intro(self) -> str:
        return (self._load_config().get("self_intro_prompt") or "").strip()