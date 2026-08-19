"""
Инструменты MCP-сервера Туту.
Версия: 2.2.0
Описание: Прокси-инструмент tutu_call для экономии токенов + каталог для промпта.
"""
import json
import logging
from typing import Annotated, Callable, Dict, List


logger = logging.getLogger("agent.mcp.tutu_tools")


def _schema_index(mcp_client) -> Dict[str, dict]:
    """Строит индекс схем инструментов сервера (name -> inputSchema)."""
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
    """Проверяет args против inputSchema. Возвращает текст ошибки или None."""
    props = (schema or {}).get("properties", {}) or {}
    required = (schema or {}).get("required", []) or []
    additional = (schema or {}).get("additionalProperties", False)
    known = set(props.keys())
    if props and additional is False:
        extra = [k for k in args if k not in known]
        if extra:
            allowed = ", ".join(sorted(known)) or "(нет полей)"
            return (
                f"❌ У инструмента '{tool}' нет полей: {', '.join(extra)}. "
                f"Допустимые поля: {allowed}. Не выдумывай параметры — используй только их."
            )
    missing = [r for r in required if r not in args or args.get(r) in (None, "")]
    if missing:
        return (
            f"❌ Для '{tool}' не хватает обязательных полей: {', '.join(missing)}. "
            f"Обязательные: {', '.join(required)}."
        )
    return None


def _make_proxy_tool(mcp_client) -> Callable:
    """Создает прокси-инструмент tutu_call с пред-валидацией."""
    schema_idx = _schema_index(mcp_client)
    valid_names = sorted(schema_idx.keys())

    def tutu_call(
        tool: Annotated[str, "Имя инструмента Туту из каталога системного промпта."],
        args_json: Annotated[str, "Аргументы строкой JSON. Только поля из каталога. '{}' если полей нет."] = "{}",
    ) -> str:
        """Вызывает инструмент MCP-сервера Туту. Точные имена и обязательность параметров — в разделе «Каталог инструментов Туту» системного промпта."""
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


def build_tutu_tools(mcp_client, mode: str = "proxy") -> List[Callable]:
    """Возвращает список tool-функций для агента. mode="proxy" — один умный tutu_call (рекомендуется)."""
    if mcp_client is None:
        return []
    return [_make_proxy_tool(mcp_client)]


def tutu_catalog_markdown(mcp_client, max_desc: int = 90) -> str:
    """Компактный каталог инструментов Туту для системного промпта."""
    tools = mcp_client.list_tools()
    if not tools:
        return "_MCP-сервер недоступен, каталог инструментов пуст._"
    lines = ["| Инструмент | Назначение | Параметры |", "| :--- | :--- | :--- |"]
    for t in tools:
        name = t.get("name", "?")
        desc = (t.get("description") or "").split("\n")[0].strip()
        if len(desc) > max_desc:
            desc = desc[: max_desc - 1] + "…"
        schema = t.get("inputSchema") or {}
        props = schema.get("properties", {}) or {}
        required = set(schema.get("required", []) or [])
        req = [p for p in props if p in required]
        opt = [p for p in props if p not in required]
        fields = []
        if req:
            fields.append("required: " + ", ".join(req))
        if opt:
            fields.append("optional: " + ", ".join(opt))
        fields_str = "; ".join(fields) if fields else "—"
        lines.append(f"| `{name}` | {desc} | {fields_str} |")
    return "\n".join(lines)