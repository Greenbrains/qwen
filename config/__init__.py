"""
Конфигурация приложения.
НИЖНИЙ СЛОЙ архитектуры: НЕ импортирует ничего из agent / interfaces,
иначе любой импорт изнутри agent превращается в циклический.
"""
from config.settings import Settings, get_settings
from config.destinations_loader import (
    DestinationConfig,
    DestinationsConfig,
    get_destinations_config,
    get_destination_by_id,
    get_all_destinations,
)

__all__ = [
    "Settings",
    "get_settings",
    "DestinationConfig",
    "DestinationsConfig",
    "get_destinations_config",
    "get_destination_by_id",
    "get_all_destinations",
]