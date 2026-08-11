"""
Синхронный MCP-клиент на requests.
Используется в консольном режиме. Работает по протоколу JSON-RPC 2.0,
получает и сохраняет Mcp-Session-Id из заголовков ответа.


"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import requests

from config import get_settings
from .models import (
    MCPTool,
    build_initialize_request,
    build_tool_call_request,
    build_tools_list_request,
)


class SyncMCPClient:
    """Синхронный клиент для вызова MCP-инструментов."""

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
        self.logger = logger or logging.getLogger("travel_agent.mcp.sync")
        self._settings = settings
        self._tools_cache: Optional[List[MCPTool]] = None

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

        self.initialize()

    # ------------------------------------------------------------------
    # Парсинг ответа (JSON или SSE)
    # ------------------------------------------------------------------
    def _parse_response(self, resp: requests.Response) -> Dict[str, Any]:
        """
        Разбирает ответ MCP-сервера.
        Сервер может вернуть:
        - application/json → обычный JSON
        - text/event-stream → SSE с data: строками
        - пустой ответ (202 Accepted для notification)
        """
        text = resp.text or ""
        content_type = resp.headers.get("Content-Type", "")

        if not text.strip():
            return {"jsonrpc": "2.0", "result": {}, "_empty": True}

        # 1) Обычный JSON
        if "application/json" in content_type or text.lstrip()[:1] in ("{", "["):
            try:
                return resp.json()
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

        # 3) Fallback: пробуем как JSON
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            self.logger.warning(f"MCP: не удалось распарсить ответ (len={len(text)})")
            return {"jsonrpc": "2.0", "result": {}, "_parse_error": True, "_raw": text[:500]}

    # ------------------------------------------------------------------
    # HTTP POST с обработкой сессии
    # ------------------------------------------------------------------
    def _post(self, payload: Dict[str, Any], timeout: int = 120) -> Dict[str, Any]:
        """Отправляет JSON-RPC запрос и возвращает разобранный ответ."""
        headers = dict(self.headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        self.logger.debug(f"MCP POST: {json.dumps(payload, ensure_ascii=False)[:2000]}")

        try:
            resp = requests.post(self.url, json=payload, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout:
            self.logger.error(f"MCP timeout ({timeout}s)")
            return {"error": f"Timeout {timeout}s"}
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"MCP connection error: {e}")
            return {"error": f"Connection error: {e}"}
        except Exception as e:
            self.logger.error(f"MCP request error: {e}")
            return {"error": str(e)}

        new_session_id = resp.headers.get("Mcp-Session-Id")
        if new_session_id:
            self.session_id = new_session_id

        self.logger.debug(f"MCP response: status={resp.status_code}, len={len(resp.text)}")

        if resp.status_code == 202:
            return {"jsonrpc": "2.0", "result": {}, "_accepted": True}

        if resp.status_code != 200:
            error_text = resp.text[:500] if resp.text else ""
            self.logger.error(f"MCP HTTP {resp.status_code}: {error_text}")
            return {"error": f"HTTP {resp.status_code}: {error_text}"}

        return self._parse_response(resp)

    # ------------------------------------------------------------------
    # Инициализация
    # ------------------------------------------------------------------
    def initialize(self) -> Dict[str, Any]:
        """Инициализирует сессию с MCP-сервером."""
        payload = build_initialize_request(
            request_id=str(uuid.uuid4()),
            protocol_version=self._settings.mcp_protocol_version,
            client_name=self._settings.mcp_client_name,
            client_version=self._settings.mcp_client_version,
        )
        self.logger.info("MCP initialize...")
        result = self._post(payload.model_dump(), timeout=30)

        if "error" not in result:
            self.logger.info(
                "✅ MCP сессия установлена"
                + (f" (session: {self.session_id[:12]}...)" if self.session_id else " (stateless)")
            )
            # ОБЯЗАТЕЛЬНО: notifications/initialized
            self._send_initialized_notification()
        else:
            self.logger.warning(f"⚠️  MCP init ошибка: {result.get('error')}")
        return result

    def _send_initialized_notification(self) -> None:
        """Отправляет notifications/initialized после успешного initialize."""
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        self._post(notification, timeout=15)
        self.logger.debug("MCP notifications/initialized отправлен")

    # ------------------------------------------------------------------
    # Список инструментов
    # ------------------------------------------------------------------
    def list_tools(self, use_cache: bool = True) -> List[MCPTool]:
        """Возвращает список доступных инструментов MCP."""
        if use_cache and self._tools_cache is not None:
            return self._tools_cache

        payload = build_tools_list_request(request_id=str(uuid.uuid4()))
        result = self._post(payload.model_dump(), timeout=30)

        if "error" in result:
            self.logger.error(f"MCP tools/list failed: {result['error']}")
            return []

        tools_data = result.get("result", {}).get("tools", [])
        self._tools_cache = [MCPTool(**t) for t in tools_data]
        self.logger.info(f"MCP tools/list: {len(self._tools_cache)} инструментов")
        return self._tools_cache

    # ------------------------------------------------------------------
    # Вызов инструмента
    # ------------------------------------------------------------------
    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Вызывает конкретный инструмент MCP и возвращает result.

        ВАЖНО для create_checkout_link:
        Поля из checkout_ref передаются НА ВЕРХНЕМ УРОВНЕ arguments,
        а НЕ как вложенный объект. Пример:
            arguments = {
                "product_type": "rail",
                "passengers": 1,
                **checkout_ref,  # распаковать!
            }
        """
        payload = build_tool_call_request(
            request_id=str(uuid.uuid4()),
            tool_name=tool_name,
            arguments=arguments or {},
        )
        self.logger.info(f"MCP call: {tool_name}")
        self.logger.debug(f"MCP call arguments: {json.dumps(arguments or {}, ensure_ascii=False)[:1000]}")

        result = self._post(payload.model_dump(), timeout=120)

        if "error" in result:
            self.logger.error(f"MCP call {tool_name} failed: {result['error']}")
            return {"error": result["error"], "isError": True}

        mcp_result = result.get("result", {})

        if isinstance(mcp_result, dict) and mcp_result.get("isError"):
            error_text = ""
            content = mcp_result.get("content", [])
            if content and isinstance(content[0], dict):
                error_text = content[0].get("text", "")
            self.logger.warning(f"MCP tool {tool_name} вернул ошибку: {error_text[:200]}")

        return mcp_result

    def close(self) -> None:
        """Закрывает клиент (очищает кэш)."""
        self._tools_cache = None