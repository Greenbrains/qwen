"""
Статические определения всех 16 MCP-инструментов сервера Туту.

Каждый инструмент описан в формате, понятном OpenAI-совместимому API Yandex
(тип "function"). Эти определения используются, когда MCP-сервер не
предоставляет список инструментов через tools/list, либо как fallback.

Категории:
- SEARCH_TOOLS      — поисковые (search_*)
- INSTRUCTION_TOOLS — плейбуки (get_*_instructions)
- DETAIL_TOOLS      — детализация (get_offer_details, get_rail_seatmap)
- ACTION_TOOLS      — действия (create_checkout_link)
- RESOURCE_TOOLS    — ресурсы (fetch_resource)
"""

from __future__ import annotations

from typing import Dict, List

# ----------------------------------------------------------------------
# Поисковые инструменты
# ----------------------------------------------------------------------
SEARCH_TOOLS: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": (
                "Поиск отелей в базе Туту по названию города, geo_id или координатам "
                "на заданные даты. Возвращает варианты с ценами, рейтингом, удобствами "
                "и правилами отмены."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {"type": "string", "description": "Название города"},
                    "geo_id": {"type": "string", "description": "Внутренний ID геообъекта"},
                    "check_in": {"type": "string", "description": "Дата заезда YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "Дата выезда YYYY-MM-DD"},
                    "guests": {"type": "integer", "description": "Количество гостей"},
                },
                "required": ["check_in", "check_out"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_avia",
            "description": (
                "Поиск авиабилетов между городами или аэропортами. Поддерживает коды IATA "
                "(SVO, LED) и названия городов. Возвращает рейсы, цены, время в пути, пересадки."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Город или код IATA отправления"},
                    "destination": {"type": "string", "description": "Город или код IATA прибытия"},
                    "departure_date": {"type": "string", "description": "Дата вылета YYYY-MM-DD"},
                    "passengers": {"type": "integer", "description": "Количество пассажиров"},
                },
                "required": ["origin", "destination", "departure_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_rail",
            "description": (
                "Поиск билетов на поезда РЖД между городами. Возвращает станции, расписание, "
                "типы вагонов (плацкарт, купе, СВ, сидячий) и доступные места."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string", "description": "Город отправления"},
                    "to_city": {"type": "string", "description": "Город прибытия"},
                    "departure_date": {"type": "string", "description": "Дата отправления YYYY-MM-DD"},
                    "passengers": {"type": "integer", "description": "Количество пассажиров"},
                    "sort": {"type": "string", "description": "Сортировка (departure_asc и т.д.)"},
                },
                "required": ["from_city", "to_city", "departure_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_bus",
            "description": (
                "Поиск междугородних автобусных билетов. Возвращает цену, варианты рейсов "
                "(прямые или с пересадками), время в пути, автовокзалы."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Город отправления"},
                    "destination": {"type": "string", "description": "Город прибытия"},
                    "departure_date": {"type": "string", "description": "Дата отправления YYYY-MM-DD"},
                },
                "required": ["origin", "destination", "departure_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_etrain",
            "description": (
                "Поиск билетов на пригородные поезда (электрички) между городами или станциями. "
                "Идеально для коротких маршрутов."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Станция отправления"},
                    "destination": {"type": "string", "description": "Станция прибытия"},
                    "departure_date": {"type": "string", "description": "Дата отправления YYYY-MM-DD"},
                },
                "required": ["origin", "destination", "departure_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_multitransport",
            "description": (
                "Мультимодальный поиск маршрутов 'как добраться'. Запускает параллельный поиск "
                "по авиа, поездам, автобусам и электричкам, возвращает комбинированные варианты. "
                "НЕ передавай return_date!"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string", "description": "Город отправления"},
                    "to_city": {"type": "string", "description": "Город прибытия"},
                    "departure_date": {"type": "string", "description": "Дата отправления YYYY-MM-DD"},
                    "adults": {"type": "integer", "description": "Количество взрослых"},
                    "optimize_for": {"type": "string", "description": "price или time"},
                },
                "required": ["from_city", "to_city", "departure_date"],
            },
        },
    },
]

# ----------------------------------------------------------------------
# Инструкции (плейбуки)
# ----------------------------------------------------------------------
INSTRUCTION_TOOLS: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_avia_instructions",
            "description": "Инструкция по авиабилетам: разрешение неоднозначности аэропортов, коды IATA, багаж, данные пассажиров.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rail_instructions",
            "description": "Инструкция по ж/д билетам: get_rail_seatmap, пагинация схемы вагона, типы мест, выбор мест для группы, паспортные данные.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bus_instructions",
            "description": "Инструкция по автобусам: правила указания пассажиров, ценообразование за группу, данные для чекаута, документы.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_etrain_instructions",
            "description": "Инструкция по электричкам: интерпретация vehicle_meta, переформатирование через get_offer_details, оформление покупки.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hotels_instructions",
            "description": "Инструкция по отелям: подводные камни с geo_id, уточняющие вопросы, формирование best_offer, правила отмены.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_multitransport_instructions",
            "description": "Инструкция по мультимодальным маршрутам: вложенные variants[], optimize_for, обработка soft-fail, сборка маршрута.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# ----------------------------------------------------------------------
# Детализация
# ----------------------------------------------------------------------
DETAIL_TOOLS: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_offer_details",
            "description": (
                "Получение детальной информации по конкретному предложению (офферу). "
                "view='compact' ограничивает фото и технические детали."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "offer_id": {"type": "string", "description": "ID предложения"},
                    "view": {"type": "string", "description": "compact или full"},
                },
                "required": ["offer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rail_seatmap",
            "description": "Чтение схемы вагона (сидений/полок) для выбранного предложения РЖД.",
            "parameters": {
                "type": "object",
                "properties": {
                    "offer_id": {"type": "string", "description": "ID предложения РЖД"},
                    "car_number": {"type": "integer", "description": "Номер вагона"},
                },
                "required": ["offer_id"],
            },
        },
    },
]

# ----------------------------------------------------------------------
# Действия
# ----------------------------------------------------------------------
ACTION_TOOLS: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "create_checkout_link",
            "description": (
                "Генерация ссылки на оформление заказа (чекаут) ранее найденного предложения. "
                "Принимает поля из найденного оффера и данные пассажиров."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "offer_id": {"type": "string", "description": "ID предложения"},
                    "passengers": {
                        "type": "array",
                        "description": "Список пассажиров",
                        "items": {
                            "type": "object",
                            "properties": {
                                "first_name": {"type": "string"},
                                "last_name": {"type": "string"},
                                "birth_date": {"type": "string"},
                                "document_type": {"type": "string"},
                            },
                        },
                    },
                },
                "required": ["offer_id"],
            },
        },
    },
]

# ----------------------------------------------------------------------
# Ресурсы
# ----------------------------------------------------------------------
RESOURCE_TOOLS: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "fetch_resource",
            "description": (
                "Чтение серверного ресурса по протоколу tutu:// и возврат его содержимого "
                "(справочники городов, аэропортов, типов документов)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "uri": {"type": "string", "description": "URI ресурса, например tutu://dictionary/airports"},
                },
                "required": ["uri"],
            },
        },
    },
]

# ----------------------------------------------------------------------
# Сводный список
# ----------------------------------------------------------------------
ALL_TOOLS: List[Dict] = (
    SEARCH_TOOLS
    + INSTRUCTION_TOOLS
    + DETAIL_TOOLS
    + ACTION_TOOLS
    + RESOURCE_TOOLS
)

# Маппинг имя -> категория (для удобства)
TOOL_CATEGORIES: Dict[str, str] = {}
for _cat, _tools in [
    ("search", SEARCH_TOOLS),
    ("instruction", INSTRUCTION_TOOLS),
    ("detail", DETAIL_TOOLS),
    ("action", ACTION_TOOLS),
    ("resource", RESOURCE_TOOLS),
]:
    for _t in _tools:
        TOOL_CATEGORIES[_t["function"]["name"]] = _cat
