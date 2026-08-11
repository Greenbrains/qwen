"""
Конфигурация приложения.
НИЖНИЙ СЛОЙ архитектуры: НЕ импортирует ничего из agent / interfaces,
иначе любой импорт изнутри agent превращается в циклический.
"""
from config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]