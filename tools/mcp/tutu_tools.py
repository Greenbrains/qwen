"""
Инструменты MCP-сервера Туту в виде Python-функций для агента.

Стратегия v3 — «умный прокси» (исправление после ревизии логов)
---------------------------------------------------------------
Диагноз по логам:
  * Модель угадывала имена полей (`from_city`, `passengers`, `arrival_before`),
    а сервер Туту жёстко валидирует аргументы (`extra_forbidden`, `required`).
  * Прокси-режим v2 экономил токены, но давал модели ТОЛЬКО обрезанный
    однострочный каталог → модель не видела точных параметров и галлюцинировала.

Решение — сохранить экономный один инструмент `tutu_call`, но:
  1. В системный промпт класть КОМПАКТНЫЙ, но ПОЛНЫЙ каталог параметров каждого
     инструмента (имя • назначение • required • optional), построенный из
     реального `inputSchema` сервера (tools/list). См. tutu_catalog_markdown().
  2. Прокси делает КЛИЕНТСКУЮ пред-валидацию args против inputSchema ДО вызова
     сервера: ловит неизвестные и отсутствующие обязательные поля и возвращает
     точную подсказку модели (без сетевого round-trip и лишних токенов ответа).
  3. Нормализует типы (число-строка "1" → 1) и чистит None.

Режимы build_tutu_tools:
  * mode="proxy"  (по умолчанию) — один tutu_call с пред-валидацией;
  * mode="expand"                — по функции на инструмент (совместимость).
"""
from __future__ import annotations

import json
import logging
from typing import Annotated, Callable, Dict, List

logger = logging.getLogger("agent.mcp.tools")


# ----------------------------------------------------------------------
# Индекс схем инструментов сервера (name -> inputSchema)
# ----------------------------------------------------------------------
def _schema_index(mcp_client) -> Dict[str, dict]:
    idx = {}
    for t in mcp_client.list_tools():
        name = t.get("name")
        if name:
            idx[name] = t.get("inputSchema") or {"type": "object", "properties": {}}
    return idx


def _coerce_types(args: dict, schema: dict) -> dict:
    """Мягкое приведение типов по JSON-схеме (например '1' -> 1 для integer)."""
    props = (schema or {}).get("properties", {}) or {}
    out = {}
    for k, v in args.items():
        spec = props.get(k, {})
        t = spec.get("type")
        try:
            if t == "integer" and isinstance(v, str) and v.strip().lstrip("-").isdigit():
                v = int(v)
            elif t == "number" and isinstance(v, str):
                v = float(v)
            elif t == "boolean" and isinstance(v, str):
                v = v.strip().lower() in ("true", "1", "yes", "да")
        except (ValueError, AttributeError):
            pass
        out[k] = v
    return out


def _validate_args(tool: str, args: dict, schema: dict) -> str | None:
    """Проверяет args против inputSchema. Возвращает текст ошибки-подсказки или None."""
    props = (schema or {}).get("properties", {}) or {}
    required = (schema or {}).get("required", []) or []
    additional = (schema or {}).get("additionalProperties", False)

    known = set(props.keys())
    # лишние поля — только если сервер их запрещает
    if props and additional is False:
        extra = [k for k in args if k not in known]
        if extra:
            allowed = ", ".join(sorted(known)) or "(нет полей)"
            return (
                f"❌ У инструмента '{tool}' нет полей: {', '.join(extra)}. "
                f"Допустимые поля: {allowed}. Не выдумывай параметры — используй только их."
            )
    # отсутствующие обязательные
    missing = [r for r in required if r not in args or args.get(r) in (None, "")]
    if missing:
        return (
            f"❌ Для '{tool}' не хватает обязательных полей: {', '.join(missing)}. "
            f"Обязательные: {', '.join(required)}."
        )
    return None


# ----------------------------------------------------------------------
# Прокси-режим (экономный + умная валидация)
# ----------------------------------------------------------------------
def _make_proxy_tool(mcp_client) -> Callable:
    schema_idx = _schema_index(mcp_client)
    valid_names = sorted(schema_idx.keys())

    def tutu_call(
        tool: Annotated[str, "Имя инструмента Туту из «Каталога инструментов Туту» системного промпта (напр. 'search_avia')."],
        args_json: Annotated[str, "Аргументы инструмента строкой JSON. Используй ТОЛЬКО поля из каталога. Пример: '{\"origin\":\"Москва\",\"destination\":\"Сочи\",\"departure_date\":\"2026-08-15\",\"adults\":1}'. '{}' если полей нет."] = "{}",
    ) -> str:
        """Вызывает инструмент MCP-сервера Туту. Точные имена и обязательность параметров каждого инструмента — в разделе «Каталог инструментов Туту» системного промпта. Используй ТОЛЬКО перечисленные там поля."""
        try:
            args = json.loads(args_json) if args_json and args_json.strip() else {}
        except json.JSONDecodeError as e:
            return f"❌ args_json не является корректным JSON: {e}. Передай строку вида '{{\"key\": \"value\"}}'."
        if not isinstance(args, dict):
            return "❌ args_json должен быть JSON-объектом (словарём)."

        if valid_names and tool not in valid_names:
            return f"❌ Инструмент '{tool}' не найден на сервере Туту. Доступные: {', '.join(valid_names)}"

        schema = schema_idx.get(tool, {})
        args = {k: v for k, v in args.items() if v is not None}
        args = _coerce_types(args, schema)

        # клиентская пред-валидация — экономит round-trip и токены на ошибках сервера
        err = _validate_args(tool, args, schema)
        if err:
            logger.info("tutu_call pre-validation reject: %s %s", tool, args)
            return err

        logger.debug("tutu_call -> %s(%s)", tool, args)
        return mcp_client.call_tool(tool, args)

    tutu_call._tool_name = "tutu_call"
    tutu_call._tool_description = tutu_call.__doc__
    params = {
        "type": "object",
        "properties": {
            "tool": {"type": "string", "description": "Имя инструмента Туту из каталога системного промпта."},
            "args_json": {"type": "string", "description": "Аргументы строкой JSON. Только поля из каталога. '{}' если полей нет."},
        },
        "required": ["tool"],
    }
    if valid_names:
        params["properties"]["tool"]["enum"] = valid_names
    tutu_call._tool_schema = {
        "type": "function",
        "function": {"name": "tutu_call", "description": tutu_call.__doc__, "parameters": params},
    }
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

    mode="proxy"  — один умный tutu_call с пред-валидацией (рекомендуется);
    mode="expand" — по функции на инструмент (дороже по токенам).
    """
    if mcp_client is None:
        return []
    if mode == "expand":
        return _make_expanded_tools(mcp_client)
    return [_make_proxy_tool(mcp_client)]


# ----------------------------------------------------------------------
# Каталог параметров для системного промпта
# ----------------------------------------------------------------------
def _fmt_fields(schema: dict) -> str:
    props = (schema or {}).get("properties", {}) or {}
    required = set((schema or {}).get("required", []) or [])
    if not props:
        return "—"
    req = [p for p in props if p in required]
    opt = [p for p in props if p not in required]
    parts = []
    if req:
        parts.append("required: " + ", ".join(req))
    if opt:
        parts.append("optional: " + ", ".join(opt))
    return "; ".join(parts)


def tutu_catalog_markdown(mcp_client, max_desc: int = 90) -> str:
    """Компактный, но ПОЛНЫЙ по параметрам каталог инструментов Туту.

    Одна строка на инструмент: имя • краткое назначение • точные поля
    (required/optional из inputSchema сервера). Именно этого не хватало модели.
    """
    tools = mcp_client.list_tools()
    if not tools:
        return tutu_catalog_markdown_fallback()
    lines = ["| Инструмент | Назначение | Параметры |", "| :--- | :--- | :--- |"]
    for t in tools:
        name = t.get("name", "?")
        desc = (t.get("description") or "").split("\n")[0].strip()
        if len(desc) > max_desc:
            desc = desc[: max_desc - 1] + "…"
        fields = _fmt_fields(t.get("inputSchema") or {})
        lines.append(f"| `{name}` | {desc} | {fields} |")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# Статический каталог-fallback (если tools/list недоступен)
# ----------------------------------------------------------------------
TUTU_TOOLS_FALLBACK = [
    ("search_avia", "Авиабилеты между городами/IATA.", "required: origin, destination, departure_date; optional: adults, sort"),
    ("search_rail", "Ж/д билеты РЖД.", "required: origin, destination, departure_date; optional: passengers, sort, page_size"),
    ("search_bus", "Междугородние автобусы.", "required: origin, destination, departure_date"),
    ("search_etrain", "Пригородные поезда (электрички).", "required: origin, destination, departure_date"),
    ("search_multitransport", "Мультимодальный «как добраться». НЕ передавать return_date.", "required: origin, destination, departure_date; optional: adults, modes, page_size"),
    ("search_hotels", "Отели по городу/geo_id.", "required: check_in, check_out; optional: city_name, geo_id, guests"),
    ("get_avia_instructions", "Плейбук по авиа.", "—"),
    ("get_rail_instructions", "Плейбук по жд.", "—"),
    ("get_bus_instructions", "Плейбук по автобусам.", "—"),
    ("get_etrain_instructions", "Плейбук по электричкам.", "—"),
    ("get_hotels_instructions", "Плейбук по отелям.", "—"),
    ("get_multitransport_instructions", "Плейбук по мультимодальным маршрутам.", "—"),
    ("get_offer_details", "Детали оффера. view=compact|full.", "required: offer_id; optional: view"),
    ("get_rail_seatmap", "Схема вагона РЖД.", "required: offer_id; optional: car_number"),
    ("create_checkout_link", "Ссылка на оформление.", "required: offer_id; optional: passengers, product_type"),
    ("fetch_resource", "Чтение ресурса tutu:// (справочники).", "required: uri"),
]


def tutu_catalog_markdown_fallback() -> str:
    lines = ["| Инструмент | Назначение | Параметры |", "| :--- | :--- | :--- |"]
    for name, desc, fields in TUTU_TOOLS_FALLBACK:
        lines.append(f"| `{name}` | {desc} | {fields} |")
    return "\n".join(lines)
