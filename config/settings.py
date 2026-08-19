"""
Конфигурация проекта.
Version: 5.3.0
Description: Переменные окружения + архитектурные константы.
"""
from datetime import datetime
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Секреты (обязательные)
    yandex_api_key: str
    yandex_folder_id: str

    # Модели (актуальные имена из каталога Яндекс AI Studio)
    # YANDEX_MODEL=qwen3.6-35b-a3b
    # YANDEX_MODEL_ROUTER=aliceai-llm-flash/latest   # ← САМАЯ ДЕШЁВАЯ для роутинга!
    # YANDEX_MODEL_AGENT=qwen3.6-35b-a3b/latest  # ← Оптимальная цена/качество
    # YANDEX_MODEL_EXPERT=deepseek-v4-flash/latest  # ← Только для сложных задач
    yandex_model_router: str = "aliceai-llm-flash/latest"      # Самая дешёвая для роутинга
    yandex_model_agent: str = "qwen3.6-35b-a3b/latest"         # Оптимальная цена/качество
    yandex_model_expert: str = "deepseek-v4-flash/latest"      # Только для сложных задач
    yandex_model_general: str = "qwen3.6-35b-a3b"              # Для простых запросов без инструментов

    # Системные настройки
    log_file: str = "logs.txt"
    system_version: str = "main_v5.3_os"

    # Архитектурные константы
    yandex_base_url: str = "https://ai.api.cloud.yandex.net/v1"
    tutu_mcp_url: str = "https://mcp.tutu.ru/mcp"
    skills_dir: Path = Path(".agents/skills")
    prompts_dir: Path = Path(".agents/prompts")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def get_model_uri(self, model_name: str) -> str:
        """Формирует полный model URI для Яндекс API: gpt://{folder_id}/{model}."""
        if model_name.startswith("gpt://") or model_name.startswith("ds://"):
            return model_name
        return f"gpt://{self.yandex_folder_id}/{model_name}"

    def get_current_date_context(self) -> str:
        """Возвращает контекст текущей даты для агентов."""
        now = datetime.now()
        weekday = now.strftime("%A")
        return (
            f"Сегодня {now.strftime('%d.%m.%Y')}, {weekday}. "
            f"НЕ предлагай даты в прошлом (2024 год, вчерашний день) или далёком будущем."
        )


def get_settings() -> Settings:
    return Settings()
