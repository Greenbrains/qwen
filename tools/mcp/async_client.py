"""
Асинхронный MCP-клиент на aiohttp.
Используется в FastAPI и WebSocket-режиме. Имеет те же методы, что и
SyncMCPClient, но возвращает coroutine.

Исправлено:
1. Относительные импорты (models из того же пакета).
2. notifications/initialized после initialize.
3. Парсинг SSE (text/event-stream).
4. Timeout для call_tool = 120 сек.
5. call_tool принимает ОБА порядка аргументов:
   call_tool("search_rail", {...})                      — новый стиль
   call_tool("search_rail", {...}, session=s)           — новый стиль с сессией
   call_tool(s, "search_rail", {...})                   — старый стиль (legacy)
   Если сессию не передали — клиент создаёт свою (лениво).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import aiohttp

from config import get_settings
from .models import (
    MCPTool,
    build_initialize_request,
    build_tool_call_request,
    build_tools_list_request,
)


class AsyncMCPClient:
    """Асинхронный клиент для вызова MCP-инструментов."""

    def __init__(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
        settings=None,
    ):
        settings = settings or get_settings()
        self.url = url or settings.mcp_url
        self.session_id: Optional[str] = None
        self.logger = logger or logging.getLogger("travel_agent.mcp.async")
        self._settings = settings
        self._tools_cache: Optional[List[MCPTool]] = None
        self._own_session: Optional[aiohttp.ClientSession] = None

        # Базовые заголовки — точно как в рабочем main_tests.py
        self.headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": settings.mcp_protocol_version,
            "User-Agent": f"{settings.mcp_client_name}/{settings.mcp_client_version}",
        }

        if headers:
            self.headers.update(headers)
        elif settings.mcp_headers:
            self.headers.update(settings.mcp_headers)

    # ------------------------------------------------------------------
    # Собственная aiohttp-сессия (ленивая)
    # ------------------------------------------------------------------
    async def _get_session(self) -> aiohttp.ClientSession:
        """Создаёт свою сессию, если внешнюю не передали."""
        if self._own_session is None or self._own_session.closed:
            self._own_session = aiohttp.ClientSession()
        return self._own_session

    # ------------------------------------------------------------------
    # Парсинг ответа (JSON или SSE)
    # ------------------------------------------------------------------
    def _parse_response_body(self, text: str, content_type: str) -> Dict[str, Any]:
        """Разбирает тело ответа: JSON или SSE."""
        if not text.strip():
            return {"jsonrpc": "2.0", "result": {}, "_empty": True}

        # 1) Обычный JSON
        if "application/json" in content_type or text.lstrip()[:1] in ("{", "["):
            try:
                return json.loads(text)
            except (json.JSONDecodeError, ValueError):
                pass

        # 2) SSE (text/event-stream)
        if (
            "text/event-stream" in content_type
            or text.lstrip().startswith(("event:", "data:"))
            or "\ndata:" in text
        ):
            events = []
            for raw_line in text.splitlines():
                raw_line = raw_line.strip()
                if raw_line.startswith("data:"):
                    data = raw_line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        events.append(json.loads(data))
                    except (json.JSONDecodeError, ValueError):
                        pass

            if events:
                for event in reversed(events):
                    if isinstance(event, dict) and ("result" in event or "error" in event):
                        return event
                return events[-1]

        # 3) Fallback
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            self.logger.warning(f"MCP: не удалось распарсить ответ (len={len(text)})")
            return {"jsonrpc": "2.0", "result": {}, "_parse_error": True, "_raw": text[:500]}

    # ------------------------------------------------------------------
    # HTTP POST с обработкой сессии
    # ------------------------------------------------------------------
    async def _post(
        self,
        session: aiohttp.ClientSession,
        payload: Dict[str, Any],
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """Отправляет JSON-RPC запрос и возвращает разобранный ответ."""
        headers = dict(self.headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        try:
            # default=str — защита от случайной сериализации несериализуемых объектов
            self.logger.debug(
                f"MCP POST: {json.dumps(payload, ensure_ascii=False, default=str)[:2000]}"
            )
            async with session.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                new_session_id = resp.headers.get("Mcp-Session-Id")
                if new_session_id:
                    self.session_id = new_session_id

                text = await resp.text()
                content_type = resp.headers.get("Content-Type", "")

                self.logger.debug(f"MCP response: status={resp.status}, len={len(text)}")

                if resp.status == 202:
                    return {"jsonrpc": "2.0", "result": {}, "_accepted": True}

                if resp.status != 200:
                    error_text = text[:500] if text else ""
                    self.logger.error(f"MCP HTTP {resp.status}: {error_text}")
                    return {"error": f"HTTP {resp.status}: {error_text}"}

                return self._parse_response_body(text, content_type)

        except aiohttp.ClientError as e:
            self.logger.error(f"MCP connection error: {e}")
            return {"error": f"Connection error: {e}"}
        except Exception as e:
            self.logger.error(f"MCP request error: {e}")
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Инициализация
    # ------------------------------------------------------------------
    async def initialize(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Инициализирует сессию с MCP-сервером."""
        payload = build_initialize_request(
            request_id=str(uuid.uuid4()),
            protocol_version=self._settings.mcp_protocol_version,
            client_name=self._settings.mcp_client_name,
            client_version=self._settings.mcp_client_version,
        )
        self.logger.info("MCP initialize...")
        result = await self._post(session, payload.model_dump(), timeout=30)

        if "error" not in result:
            self.logger.info(
                "✅ MCP сессия установлена"
                + (f" (session: {self.session_id[:12]}...)" if self.session_id else " (stateless)")
            )
            await self._send_initialized_notification(session)
        else:
            self.logger.warning(f"⚠️  MCP init ошибка: {result.get('error')}")
        return result

    async def _send_initialized_notification(self, session: aiohttp.ClientSession) -> None:
        """Отправляет notifications/initialized после успешного initialize."""
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        await self._post(session, notification, timeout=15)
        self.logger.debug("MCP notifications/initialized отправлен")

    # ------------------------------------------------------------------
    # Список инструментов
    # ------------------------------------------------------------------
    async def list_tools(
        self, session: aiohttp.ClientSession, use_cache: bool = True
    ) -> List[MCPTool]:
        """Возвращает список доступных инструментов MCP."""
        if use_cache and self._tools_cache is not None:
            return self._tools_cache

        payload = build_tools_list_request(request_id=str(uuid.uuid4()))
        result = await self._post(session, payload.model_dump(), timeout=30)

        if "error" in result:
            self.logger.error(f"MCP tools/list failed: {result['error']}")
            return []

        tools_data = result.get("result", {}).get("tools", [])
        self._tools_cache = [MCPTool(**t) for t in tools_data]
        self.logger.info(f"MCP tools/list: {len(self._tools_cache)} инструментов")
        return self._tools_cache

    # ------------------------------------------------------------------
    # Вызов инструмента (гибкая сигнатура — ключевой фикс)
    # ------------------------------------------------------------------
    async def call_tool(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Вызывает инструмент MCP. Поддерживает все три варианта вызова:

            1) call_tool("search_rail", {...})                        — НОВЫЙ (рекомендуется)
            2) call_tool("search_rail", {...}, session=http_session)  — новый с явной сессией
            3) call_tool(http_session, "search_rail", {...})          — legacy

        Если сессию не передали — клиент использует собственную (ленивую).

        ВАЖНО для create_checkout_link:
        Поля из checkout_ref передаются НА ВЕРХНЕМ УРОВНЕ arguments,
        а НЕ как вложенный объект. Пример:
            arguments = {
                "product_type": "rail",
                "passengers": 1,
                **checkout_ref,  # распаковать!
            }
        """
        session = kwargs.pop("session", None)

        if len(args) >= 2 and isinstance(args[0], aiohttp.ClientSession):
            # legacy: (session, tool_name, arguments)
            session = args[0]
            tool_name = args[1]
            arguments = args[2] if len(args) > 2 else kwargs.pop("arguments", None)
        elif len(args) >= 1:
            # новый стиль: (tool_name, arguments)
            tool_name = args[0]
            arguments = args[1] if len(args) > 1 else kwargs.pop("arguments", None)
        else:
            tool_name = kwargs.pop("tool_name")
            arguments = kwargs.pop("arguments", None)

        # Если сессию не передали — создаём свою
        session = session or await self._get_session()

        payload = build_tool_call_request(
            request_id=str(uuid.uuid4()),
            tool_name=tool_name,
            arguments=arguments or {},
        )
        self.logger.info(f"MCP call: {tool_name}")
        self.logger.debug(
            f"MCP call arguments: {json.dumps(arguments or {}, ensure_ascii=False, default=str)[:1000]}"
        )

        result = await self._post(session, payload.model_dump(), timeout=120)

        if "error" in result:
            self.logger.error(f"MCP call {tool_name} failed: {result['error']}")
            return {"error": result["error"], "isError": True}

        mcp_result = result.get("result", {})

        # Проверяем isError на уровне MCP
        if isinstance(mcp_result, dict) and mcp_result.get("isError"):
            error_text = ""
            content = mcp_result.get("content", [])
            if content and isinstance(content[0], dict):
                error_text = content[0].get("text", "")
            self.logger.warning(f"MCP tool {tool_name} вернул ошибку: {error_text[:200]}")

        return mcp_result

    # ------------------------------------------------------------------
    # Очистка
    # ------------------------------------------------------------------
    async def close(self) -> None:
        """Очищает кэш и закрывает собственную сессию (async!)."""
        self._tools_cache = None
        if self._own_session is not None and not self._own_session.closed:
            await self._own_session.close()