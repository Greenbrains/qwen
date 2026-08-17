"""
Инструменты MCP-сервера Туту в виде Python-функций для агента.

Стратегия экономии токенов (v2)
--------------------------------
Ранее все ~16 инструментов Туту (каждый с полной JSON-схемой и описанием)
инжектились в поле `tools` на КАЖДОМ шаге агента. При 25 итерациях это давало
кратный перерасход токенов на статичные схемы.

Новый подход — «прокси-инструмент»:
  * агенту выдаётся ОДИН инструмент `tutu_call(tool, args_json)`;
  * список конкретных tutu-инструментов и их назначение живут в системном
    промпте в виде КОРОТКОГО markdown-каталога (одна строка на инструмент);
  * агент вызывает tutu_call(tool="search_avia", args_json='{"origin": ...}').

Плюсы:
  * фиксированный, маленький вклад в prompt tokens независимо от числа
    инструментов на сервере;
  * MCP-сервер остаётся источником истины: реальный список берётся через
    tools/list, а прокси лишь ретранслирует вызовы.

Функция `build_tutu_tools(mcp_client, mode=...)` возвращает список tool-функций:
  * mode="proxy" (по умолчанию) — один tutu_call (экономно);
  * mode="expand"                — по одной функции на инструмент (совместимость
                                    со старым поведением, дороже по токенам).
"""
from __future__ import annotations

import json
import logging
from typing import Annotated, Callable, List

logger = logging.getLogger("agent.mcp.tools")


# ----------------------------------------------------------------------
# Прокси-режим (экономный, по умолчанию)
# ----------------------------------------------------------------------
def _make_proxy_tool(mcp_client) -> Callable:
    valid_names = set(mcp_client.tool_names())

    def tutu_call(
        tool: Annotated[str, "Имя инструмента Туту из каталога, напр. 'search_avia', 'search_rail', 'search_hotels'."],
        args_json: Annotated[str, "Аргументы инструмента в виде JSON-строки, напр. '{\"origin\":\"Москва\",\"destination\":\"Сочи\",\"departure_date\":\"2026-08-15\"}'. Пустой объект '{}' если аргументов нет."] = "{}",
    ) -> str:
        """Вызывает инструмент MCP-сервера Туту (авиа/жд/автобусы/отели/детали/чекаут). Имя инструмента и его параметры смотри в разделе «Каталог инструментов Туту» системного промпта."""
        try:
            args = json.loads(args_json) if args_json and args_json.strip() else {}
        except json.JSONDecodeError as e:
            return f"❌ args_json не является корректным JSON: {e}. Передай строку вида '{{\"key\": \"value\"}}'."
        if not isinstance(args, dict):
            return "❌ args_json должен быть JSON-объектом (словарём)."

        if valid_names and tool not in valid_names:
            hint = ", ".join(sorted(valid_names))
            return f"❌ Инструмент '{tool}' не найден на сервере Туту. Доступные: {hint}"

        # чистим None
        args = {k: v for k, v in args.items() if v is not None}
        logger.debug("tutu_call -> %s(%s)", tool, args)
        return mcp_client.call_tool(tool, args)

    tutu_call._tool_name = "tutu_call"
    tutu_call._tool_description = tutu_call.__doc__
    tutu_call._tool_schema = {
        "type": "function",
        "function": {
            "name": "tutu_call",
            "description": tutu_call.__doc__,
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {
                        "type": "string",
                        "description": "Имя инструмента Туту из каталога системного промпта.",
                        "enum": sorted(valid_names) if valid_names else None,
                    },
                    "args_json": {
                        "type": "string",
                        "description": "Аргументы в виде JSON-строки. '{}' если аргументов нет.",
                    },
                },
                "required": ["tool"],
            },
        },
    }
    # убираем enum:null, если имён не получили
    if not valid_names:
        tutu_call._tool_schema["function"]["parameters"]["properties"]["tool"].pop("enum", None)
    return tutu_call


# ----------------------------------------------------------------------
# Expand-режим (по функции на инструмент — совместимость)
# ----------------------------------------------------------------------
def _make_expanded_tools(mcp_client) -> List[Callable]:
    tools_defs = mcp_client.list_tools()
    functions: List[Callable] = []
    type_map = {"string": str, "integer": int, "number": float, "boolean": bool, "array": list, "object": dict}

    for t_def in tools_defs:
        name = t_def.get("name")
        desc = t_def.get("description", "MCP tool")
        input_schema = t_def.get("inputSchema", {}) or {"type": "object", "properties": {}}

        def make_wrapper(t_name, t_desc, t_schema):
            def wrapper(**kwargs):
                clean = {k: v for k, v in kwargs.items() if v is not None}
                return mcp_client.call_tool(t_name, clean)

            wrapper.__name__ = t_name
            wrapper.__doc__ = t_desc
            annotations = {}
            for prop_name, prop_def in (t_schema.get("properties", {}) or {}).items():
                py_type = type_map.get(prop_def.get("type", "string"), str)
                annotations[prop_name] = Annotated[py_type, prop_def.get("description", "")]
            wrapper.__annotations__ = annotations
            wrapper._tool_name = t_name
            wrapper._tool_description = t_desc
            wrapper._tool_schema = {
                "type": "function",
                "function": {"name": t_name, "description": t_desc, "parameters": t_schema},
            }
            return wrapper

        functions.append(make_wrapper(name, desc, input_schema))
    return functions


def build_tutu_tools(mcp_client, mode: str = "proxy") -> List[Callable]:
    """Возвращает список tool-функций для агента.

    mode="proxy"  — один экономный tutu_call (рекомендуется);
    mode="expand" — по функции на инструмент (дороже по токенам).
    """
    if mcp_client is None:
        return []
    if mode == "expand":
        return _make_expanded_tools(mcp_client)
    return [_make_proxy_tool(mcp_client)]


# ----------------------------------------------------------------------
# Статический каталог-fallback (используется, если tools/list недоступен).
# Держим его КОРОТКИМ: только имя + одно-строчное назначение + ключевые поля.
# ----------------------------------------------------------------------
TUTU_TOOLS_FALLBACK = [
    ("search_avia", "Авиабилеты между городами/IATA.", "origin, destination, departure_date, [passengers]"),
    ("search_rail", "Ж/д билеты РЖД (плацкарт/купе/СВ/сидячий).", "from_city, to_city, departure_date, [passengers, sort]"),
    ("search_bus", "Междугородние автобусы.", "origin, destination, departure_date"),
    ("search_etrain", "Пригородные поезда (электрички).", "origin, destination, departure_date"),
    ("search_multitransport", "Мультимодальный поиск «как добраться» (авиа+жд+бус+электрички). НЕ передавать return_date.", "from_city, to_city, departure_date, [adults, optimize_for]"),
    ("search_hotels", "Отели по городу/geo_id/координатам.", "check_in, check_out, [city_name, geo_id, guests]"),
    ("get_avia_instructions", "Плейбук по авиа (IATA, багаж, пассажиры).", "—"),
    ("get_rail_instructions", "Плейбук по жд (seatmap, места, паспорта).", "—"),
    ("get_bus_instructions", "Плейбук по автобусам.", "—"),
    ("get_etrain_instructions", "Плейбук по электричкам.", "—"),
    ("get_hotels_instructions", "Плейбук по отелям (geo_id, best_offer).", "—"),
    ("get_multitransport_instructions", "Плейбук по мультимодальным маршрутам.", "—"),
    ("get_offer_details", "Детали оффера. view=compact|full.", "offer_id, [view]"),
    ("get_rail_seatmap", "Схема вагона РЖД.", "offer_id, [car_number]"),
    ("create_checkout_link", "Ссылка на оформление заказа.", "offer_id, [passengers]"),
    ("fetch_resource", "Чтение ресурса tutu:// (справочники).", "uri"),
]


def tutu_catalog_markdown_fallback() -> str:
    lines = ["| Инструмент | Назначение | Ключевые поля |", "| :--- | :--- | :--- |"]
    for name, desc, fields in TUTU_TOOLS_FALLBACK:
        lines.append(f"| `{name}` | {desc} | {fields} |")
    return "\n".join(lines)
