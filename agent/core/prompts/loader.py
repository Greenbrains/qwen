import yaml
from datetime import datetime
from config.settings import get_settings

class PromptLoader:
    def __init__(self):
        settings = get_settings()
        with open(".agents/prompts/system.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def render_system_prompt(self, mcp_catalog_markdown: str, skill_context: str = "") -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        weekday = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"][datetime.now().weekday()]
        
        base = self.config.get('system_prompt', '')
        
        return f"""{base}

## Текущий контекст времени
Сегодня: **{today}** ({weekday}).
Все даты считай относительно этой даты.

## Каталог инструментов Туту (MCP)
{mcp_catalog_markdown}

## Инструкция навыка
{skill_context if skill_context else "Общий режим работы."}
"""