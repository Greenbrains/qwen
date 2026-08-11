"""
Обработчики событий для Yandex Realtime API (WebSocket).
Ключевая функция — handle_function_call: вызывает MCP-клиент
и отправляет результат обратно в WebSocket.

Логика соответствует эталонному примеру Yandex AI Studio SDK:
    payload = { "type": "conversation.item.create", "item": {...} }
    await ws.send_json(payload)
    await ws.send_json({"type": "response.create"})
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger("travel_agent.agent.handlers")


def process_function_call(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Формирует payload для conversation.item.create по function_call от
    Realtime API. По умолчанию возвращает {"ok": True} — реальный вызов
    MCP выполняется в handle_function_call, который переопределяет output.
    """
    call_id = item.get("call_id")
    return {
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps({"ok": True}, ensure_ascii=False),
        },
    }


async def handle_function_call(
    ws: aiohttp.ClientWebSocketResponse,
    item: Dict[str, Any],
    mcp_client,
    session: Optional[aiohttp.ClientSession] = None,
) -> Dict[str, Any]:
    """
    Вызывает MCP-клиент для function_call и отправляет результат в Yandex
    Realtime WebSocket. Возвращает отправленный payload.

    Args:
        ws: WebSocket-соединение с Yandex Realtime API.
        item: элемент function_call из Realtime API (с полями
              name, arguments, call_id).
        mcp_client: AsyncMCPClient.
        session: aiohttp.ClientSession (опционально; если None — клиент
                 создаст свою сессию лениво).
    """
    call_id = item.get("call_id")
    name = item.get("name", "")
    arguments = item.get("arguments", {})
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}

    logger.info(
        "🔧 Realtime function call: %s args=%s",
        name,
        json.dumps(arguments, ensure_ascii=False)[:200],
    )

    # --- сам вызов MCP ---
    try:
        if mcp_client is None:
            raise RuntimeError("mcp_client не инициализирован в зависимостях")
        result = await mcp_client.call_tool(name, arguments, session=session)
        output = json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("Realtime function call error: %s", e, exc_info=True)
        output = json.dumps({"error": str(e)}, ensure_ascii=False)

    # --- payload как в эталоне ---
    payload = {
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": output,
        },
    }

    if ws is not None:
        logger.info("[conversation.item.create(function_call_output)]: %r", payload)
        await ws.send_json(payload)
        logger.info("отправляем response.create после функции")
        await ws.send_json({"type": "response.create"})

    return payload