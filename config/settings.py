"""
Конфигурация проекта.
Version: 5.1.1
Description: Актуальные имена моделей (август 2026) согласно документации Яндекса.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 1. Секреты
    yandex_api_key: str
    yandex_folder_id: str
    
    # 2. Модели (официальные имена из документации Яндекса)
    yandex_model: str = "yandexgpt/latest"
    yandex_model_router: str = "aliceai-llm-flash/latest"    # ← aliceAI
    yandex_model_agent: str = "qwen3.6-35b-a3b/latest"
    yandex_model_expert: str = "deepseek-v4-flash/latest"
    
    # 3. Системные настройки
    log_file: str = "logs.txt"
    system_version: str = "main_v5.1_economy"
    
    # 4. Архитектурные константы
    yandex_base_url: str = "https://ai.api.cloud.yandex.net/v1"
    tutu_mcp_url: str = "https://mcp.tutu.ru/mcp"
    skills_dir: Path = Path(".agents/skills")
    prompts_dir: Path = Path(".agents/prompts")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


def get_settings() -> Settings:
    return Settings()