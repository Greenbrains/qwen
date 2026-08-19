"""
MCP-клиент для работы с сервером Туту.
Версия: 2.2.0
Описание: Синхронный клиент по протоколу Streamable HTTP с поддержкой SSE,
          TTL-кэшем инструментов и авто-восстановлением сессии.
"""
import itertools
import json
import logging
import time
from typing import Any, Dict, List, Optional

import requests


logger = logging.getLogger("agent.mcp.sync")

_PROTOCOL_VERSION = "2024-11-05"


class SyncMCPClient:
    """Синхронный клиент для вызова MCP-инструментов по Streamable HTTP."""

    def __init__(
        self,
        url: str = "https://mcp.tutu.ru/mcp",
        timeout: int = 60,
        headers: Optional[Dict[str, str]] = None,
        tools_ttl: int = 300,
    ):
        """Инициализация клиента с настройками подключения."""
        self.url = url
        self.timeout = timeout
        self.tools_ttl = tools_ttl
        self.session_id: Optional[str] = None
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": _PROTOCOL_VERSION,
            "User-Agent": "tutu-travel-agent/2.2.0",
        }
        if headers:
            self.headers.update(headers)
        self._tools_cache: List[Dict] = []
        self._tools_cached_at: float = 0.0
        self._initialized = False
        self._id_counter = itertools.count(1)

    def _next_id(self) -> str:
        """Генерирует монотонный ID для JSON-RPC запроса."""
        return str(next(self._id_counter))

    def _parse_sse_response(self, text: str) -> dict:
        """Парсит ответ в формате SSE (Server-Sent Events)."""
        if not text.strip():
            return {"error": "Пустой ответ от сервера"}
        if text.lstrip().startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        events = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str and data_str != "[DONE]":
                    try:
                        events.append(json.loads(data_str))
                    except json.JSONDecodeError:
                        continue
        if events:
            for event in reversed(events):
                if isinstance(event, dict) and ("result" in event or "error" in event):
                    return event
            return events[-1]
        return {"error": f"Не удалось распарсить SSE-ответ: {text[:200]}"}

    def _post(self, payload: dict, timeout: int = None) -> dict:
        """Отправляет JSON-RPC запрос и возвращает ответ."""
        headers = dict(self.headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        try:
            resp = requests.post(
                self.url, json=payload, headers=headers, timeout=timeout or self.timeout
            )
        except requests.exceptions.Timeout:
            logger.error("MCP timeout")
            return {"error": "Timeout"}
        except Exception as e:
            logger.error(f"MCP request error: {e}")
            return {"error": str(e)}
        new_session_id = resp.headers.get("Mcp-Session-Id")
        if new_session_id:
            self.session_id = new_session_id
        if resp.status_code == 202:
            return {"jsonrpc": "2.0", "result": {}, "_accepted": True}
        if resp.status_code in (400, 401, 404):
            logger.warning("MCP HTTP %s — сбрасываю сессию", resp.status_code)
            self.session_id = None
            self._initialized = False
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        if resp.status_code != 200:
            error_text = resp.text[:200] if resp.text else ""
            logger.error(f"MCP HTTP {resp.status_code}: {error_text}")
            return {"error": f"HTTP {resp.status_code}: {error_text}"}
        content_type = resp.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            return self._parse_sse_response(resp.text)
        try:
            return resp.json()
        except json.JSONDecodeError:
            return self._parse_sse_response(resp.text)

    def initialize(self) -> bool:
        """Инициализирует сессию с MCP-сервером."""
        if self._initialized:
            return True
        init_payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "tutu-travel-agent", "version": "2.2.0"},
            },
        }
        logger.info(f"MCP initialize на {self.url}...")
        result = self._post(init_payload, timeout=30)
        if "error" in result:
            logger.error(f"MCP Init Error: {result['error']}")
            return False
        logger.info(
            "✅ MCP сессия установлена"
            + (f" (session: {self.session_id[:12]}...)" if self.session_id else " (stateless)")
        )
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, timeout=15)
        self._initialized = True
        return True

    def list_tools(self, force: bool = False) -> List[Dict]:
        """Возвращает список доступных инструментов MCP с TTL-кэшем."""
        if not self._initialized and not self.initialize():
            return []
        fresh = (time.time() - self._tools_cached_at) < self.tools_ttl
        if self._tools_cache and fresh and not force:
            return self._tools_cache
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/list", "params": {}}
        result = self._post(payload, timeout=15)
        if "error" in result:
            logger.error(f"MCP tools/list failed: {result['error']}")
            return self._tools_cache
        tools_data = result.get("result", {}).get("tools", [])
        if tools_data:
            self._tools_cache = tools_data
            self._tools_cached_at = time.time()
            logger.info(f"📋 Получено {len(tools_data)} MCP-инструментов")
        return self._tools_cache

    def call_tool(self, tool_name: str, arguments: dict, _retry: bool = True) -> str:
        """Вызывает конкретный инструмент MCP и возвращает результат."""
        if not self._initialized and not self.initialize():
            return "❌ MCP не инициализирован"
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments or {}},
        }
        result = self._post(payload, timeout=120)
        if "error" in result:
            if _retry and not self._initialized:
                logger.info("Повтор call_tool после переустановки сессии")
                if self.initialize():
                    return self.call_tool(tool_name, arguments, _retry=False)
            return f"❌ MCP Error: {result['error']}"
        res = result.get("result", {}) or {}
        is_error = res.get("isError", False)
        content = res.get("content", [])
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif "text" in item:
                    text_parts.append(item["text"])
        text = "\n".join(p for p in text_parts if p) or json.dumps(res, ensure_ascii=False)
        return (f"❌ Инструмент вернул ошибку:\n{text}" if is_error else text)

    def tools_catalog_markdown(self) -> str:
        """Возвращает человекочитаемый каталог инструментов для системного промпта."""
        tools = self.list_tools()
        if not tools:
            return "_MCP-сервер недоступен, каталог инструментов пуст._"
        lines = ["| Инструмент | Назначение |", "| :--- | :--- |"]
        for t in tools:
            name = t.get("name", "?")
            desc = (t.get("description") or "").split("\n")[0][:110]
            lines.append(f"| `{name}` | {desc} |")
        return "\n".join(lines)

    def tool_names(self) -> List[str]:
        """Возвращает список имен доступных инструментов."""
        return [t.get("name") for t in self.list_tools() if t.get("name")]