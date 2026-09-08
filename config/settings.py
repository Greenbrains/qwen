"""
Конфигурация проекта.
Version: 5.5.0
Description: Переменные окружения + архитектурные константы + поддержка провайдеров.
"""
from typing import Optional, Dict
from pathlib import Path
from datetime import datetime
from functools import lru_cache
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderSettings(BaseModel):
    """Настройки одного LLM-провайдера."""
    base_url: str
    api_key: Optional[str] = None
    uri_format: str = "{model}"
    display_name: str = ""


class Settings(BaseSettings):
    # Секреты (все опциональны — активный провайдер выбирается через default_provider)
    yandex_api_key: Optional[str] = None
    yandex_folder_id: Optional[str] = None
    router_ai_key: Optional[str] = None

    # Активный провайдер: "router" | "yandex" (можно перебить через .env)
    default_provider: str = "router"

    # Модели
    yandex_model_router: str = "aliceai-llm-flash/latest"
    yandex_model_agent: str = "qwen3.6-35b-a3b/latest"
    router_model: str = "z-ai/glm-5.3-flash"

    # Системные настройки
    log_file: str = "logs.txt"
    system_version: str = "main_v5.3_os"

    # URL и пути
    yandex_base_url: str = "https://ai.api.cloud.yandex.net/v1"
    router_base_url: str = "https://routerai.ru/api/v1"
    tutu_mcp_url: str = "https://mcp.tutu.ru/mcp"
    skills_dir: Path = Path(".agents/skills")
    prompts_dir: Path = Path(".agents/prompts")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def providers(self) -> Dict[str, ProviderSettings]:
        return {
            "yandex": ProviderSettings(
                base_url=self.yandex_base_url,
                api_key=self.yandex_api_key,
                uri_format=f"gpt://{self.yandex_folder_id}/{{model}}",
                display_name="Yandex AI Studio",
            ),
            "router": ProviderSettings(
                base_url=self.router_base_url,
                api_key=self.router_ai_key,
                uri_format="{model}",
                display_name="Router AI",
            ),
        }

    @property
    def provider(self) -> ProviderSettings:
        """Активный провайдер."""
        return self.providers[self.default_provider]

    @property
    def model_router(self) -> str:
        """Модель роутера активного провайдера."""
        return self.yandex_model_router if self.default_provider == "yandex" else self.router_model

    @property
    def model_agent(self) -> str:
        """Модель исполнителя активного провайдера."""
        return self.yandex_model_agent if self.default_provider == "yandex" else self.router_model

    def build_model_uri(self, model: str) -> str:
        """URI модели для активного провайдера: gpt://{folder}/{model} или просто {model}."""
        if model.startswith(("gpt://", "ds://")):
            return model
        return self.provider.uri_format.format(model=model)

    def get_current_date_context(self) -> str:
        now = datetime.now()
        return f"Сегодня {now.strftime('%d.%m.%Y')}, {now.strftime('%A')}."


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()