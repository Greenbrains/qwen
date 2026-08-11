"""
Настройки проекта.
Загружает переменные окружения из .env и предоставляет единый объект Settings
(pydantic-класс) для доступа ко всем константам приложения.

Использование:
    from config import get_settings
    settings = get_settings()
    print(settings.mcp_url)
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Загружаем .env из корня проекта (override=True — приоритет у файла)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)


class Settings(BaseModel):
    """Единый объект конфигурации приложения."""

    # --- Yandex AI Studio (OpenAI-совместимый API) ---
    yandex_api_key_env: str = Field(
        default_factory=lambda: os.environ.get("YANDEX_API_KEY_ENV", "august2026"),
        description="Имя переменной окружения, в которой лежит API-ключ",
    )
    yandex_folder_id: str = Field(
        default_factory=lambda: os.environ.get("YANDEX_FOLDER_ID", ""),
        description="Идентификатор каталога Yandex Cloud",
    )
    yandex_model: str = Field(
        default_factory=lambda: os.environ.get("YANDEX_MODEL", "qwen3.6-35b-a3b/latest"),
        description="Имя модели (без префикса gpt://)",
    )
    yandex_base_url: str = Field(
        default="https://ai.api.cloud.yandex.net/v1",
        description="Базовый URL OpenAI-совместимого API Yandex",
    )

    # --- Yandex Realtime API (голосовой режим) ---
    yandex_realtime_model: str = Field(
        default_factory=lambda: os.environ.get(
            "YANDEX_REALTIME_MODEL", "speech-realtime-250923/latest"
        ),
        description="Модель Realtime API для голосового режима",
    )
    yandex_realtime_prompt_id: str = Field(
        default_factory=lambda: os.environ.get("YANDEX_REALTIME_PROMPT_ID", ""),
        description="ID промпта для Realtime API (опционально)",
    )

    # --- Yandex Responses API ---
    responses_prompt_id: Optional[str] = Field(
        default_factory=lambda: os.environ.get("RESPONSES_PROMPT_ID") or None,
        description="ID промпта из Yandex Responses API (формат: fvt1s90v3a4k2grhr2i2)",
    )

    # --- MCP-сервер Туту ---
    mcp_url: str = Field(
        default_factory=lambda: os.environ.get("MCP_URL", "https://mcp.tutu.ru/mcp"),
        description="URL MCP-сервера",
    )
    mcp_headers: Dict[str, str] = Field(
        default_factory=lambda: {
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        description="Заголовки для MCP-запросов",
    )
    mcp_protocol_version: str = Field(
        default="2024-11-05", description="Версия протокола MCP"
    )
    mcp_client_name: str = Field(
        default="tutu-travel-agent", description="Имя клиента для MCP initialize"
    )
    mcp_client_version: str = Field(
        default="2.0.0", description="Версия клиента для MCP initialize"
    )

    # --- Агент ---
    # Основное имя поля — max_agent_iterations (совпадает с env MAX_AGENT_ITERATIONS).
    max_agent_iterations: int = Field(
        default_factory=lambda: int(os.environ.get("MAX_AGENT_ITERATIONS", "12")),
        description="Максимальное число итераций агентного цикла",
    )
    temperature: float = Field(default=0.3, description="Температура модели")
    max_tokens: int = Field(default=4096, description="Максимум токенов в ответе")

    # --- Логирование ---
    log_file: str = Field(
        default_factory=lambda: os.environ.get("LOG_FILE", "logs.txt"),
        description="Файл технических логов",
    )
    log_level: str = Field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "DEBUG"),
        description="Уровень логирования",
    )

    # --- FastAPI ---
    api_host: str = Field(default="0.0.0.0", description="Хост FastAPI")
    api_port: int = Field(
        default_factory=lambda: int(os.environ.get("API_PORT", "8001")),
        description="Порт FastAPI",
    )

    # --- Промпты ---
    prompts_dir: str = Field(
        default="core/prompts", description="Директория с шаблонами промптов"
    )
    system_prompt_template: str = Field(
        default="system_prompt.jinja", description="Имя шаблона системного промпта"
    )

    # --- Скилы ---
    skills_enabled: bool = Field(
        default_factory=lambda: os.environ.get("SKILLS_ENABLED", "true").lower() == "true",
        description="Включать ли скилы в реестр инструментов",
    )

    # --- Свойства-хелперы ---
    @property
    def api_key(self) -> str:
        """Возвращает API-ключ из переменной окружения."""
        return os.environ.get(self.yandex_api_key_env, "")

    @property
    def max_iterations(self) -> int:
        """Алиас для max_agent_iterations (обратная совместимость)."""
        return self.max_agent_iterations

    @property
    def composite_model(self) -> str:
        """Составное имя модели вида gpt://{folder_id}/{model}."""
        return f"gpt://{self.yandex_folder_id}/{self.yandex_model}"

    @property
    def realtime_ws_url(self) -> str:
        """URL WebSocket для Realtime API."""
        return (
            "wss://ai.api.cloud.yandex.net/v1/realtime"
            f"?model=gpt://{self.yandex_folder_id}/{self.yandex_realtime_model}"
        )

    @property
    def realtime_headers(self) -> Dict[str, str]:
        """Заголовки авторизации для Realtime API."""
        return {"Authorization": f"Api-Key {self.api_key}"}

    def validate_llm(self) -> None:
        """Проверяет наличие обязательных настроек LLM."""
        if not self.api_key:
            raise RuntimeError(
                f"API-ключ не найден. Добавьте в .env: {self.yandex_api_key_env}=..."
            )
        if not self.yandex_folder_id:
            raise RuntimeError("YANDEX_FOLDER_ID не найден в .env")


@lru_cache
def get_settings() -> Settings:
    """Возвращает кэшированный экземпляр настроек."""
    return Settings()