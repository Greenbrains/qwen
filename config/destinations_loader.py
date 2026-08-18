"""
Загрузчик конфигурации направлений.
Читает config/destinations.yaml и предоставляет функции для доступа к данным.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class DestinationConfig:
    """Конфигурация одного направления."""
    destination_id: str
    name: str
    emoji: str
    description: str
    full_description: str
    skills: List[str] = field(default_factory=list)
    knowledge_files: List[str] = field(default_factory=list)


@dataclass
class DestinationsConfig:
    """Полная конфигурация направлений."""
    destinations: List[DestinationConfig] = field(default_factory=list)
    skill_tools_map: Dict[str, List[str]] = field(default_factory=dict)

    def get_destination(self, dest_id: str) -> Optional[DestinationConfig]:
        """Найти направление по ID."""
        for dest in self.destinations:
            if dest.destination_id == dest_id:
                return dest
        return None

    def get_allowed_tools(self, dest_id: str) -> List[str]:
        """
        Получить список разрешённых инструментов для направления.
        Если направление не найдено — вернуть полный набор (fallback).
        """
        dest = self.get_destination(dest_id)
        if not dest:
            # Fallback: все инструменты из всех скиллов
            all_tools = []
            for tools in self.skill_tools_map.values():
                all_tools.extend(tools)
            return all_tools

        allowed_tools = []
        for skill in dest.skills:
            if skill in self.skill_tools_map:
                allowed_tools.extend(self.skill_tools_map[skill])
        return allowed_tools

    def get_knowledge_files(self, dest_id: str) -> List[str]:
        """Получить список файлов знаний для направления."""
        dest = self.get_destination(dest_id)
        if not dest:
            return ["travel_hacks.md", "faq_tutu.md"]  # fallback
        return dest.knowledge_files


@lru_cache
def _get_config_path() -> Path:
    """Получить путь к файлу конфигурации."""
    # Ищем файл относительно корня проекта
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / "destinations.yaml"
    return config_path


@lru_cache
def get_destinations_config() -> DestinationsConfig:
    """
    Загрузить и вернуть конфигурацию направлений.
    Кэшируется после первой загрузки.
    """
    config_path = _get_config_path()

    if not config_path.exists():
        # Возвращаем пустую конфигурацию с fallback-поведением
        return DestinationsConfig()

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return DestinationsConfig()

    destinations = []
    for item in data.get("destinations", []):
        destinations.append(DestinationConfig(
            destination_id=item.get("destination_id", ""),
            name=item.get("name", ""),
            emoji=item.get("emoji", ""),
            description=item.get("description", ""),
            full_description=item.get("full_description", ""),
            skills=item.get("skills", []),
            knowledge_files=item.get("knowledge_files", []),
        ))

    skill_tools_map = data.get("skill_tools_map", {})

    return DestinationsConfig(
        destinations=destinations,
        skill_tools_map=skill_tools_map,
    )


def get_destination_by_id(dest_id: str) -> Optional[DestinationConfig]:
    """Получить конфигурацию направления по ID."""
    config = get_destinations_config()
    return config.get_destination(dest_id)


def get_all_destinations() -> List[DestinationConfig]:
    """Получить список всех направлений."""
    config = get_destinations_config()
    return config.destinations


def get_allowed_tools_for_destination(dest_id: str) -> List[str]:
    """Получить список разрешённых инструментов для направления."""
    config = get_destinations_config()
    return config.get_allowed_tools(dest_id)


def get_knowledge_files_for_destination(dest_id: str) -> List[str]:
    """Получить список файлов знаний для направления."""
    config = get_destinations_config()
    return config.get_knowledge_files(dest_id)