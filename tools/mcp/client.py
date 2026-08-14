"""
Синхронный MCP-клиент на requests с поддержкой SSE.
Используется в консольном агенте (ft_assistant2026).
"""
import json
import logging
import requests
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger("agent.mcp.sync")

class SyncMCPClient:
    """Синхронный клиент для вызова MCP-инструментов."""
    
    def __init__(self, url: str = "https://mcp.tutu.ru/mcp", timeout: int = 60, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2024-11-05",
            "User-Agent": "tutu-travel-agent/2.0.0",
        }
        if headers:
            self.headers.update(headers)
        self._tools_cache: List[Dict] = []
        self._initialized = False
        
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
        headers = dict(self.headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
            
        try:
            resp = requests.post(
                self.url, 
                json=payload, 
                headers=headers, 
                timeout=timeout or self.timeout
            )
            
            new_session_id = resp.headers.get("Mcp-Session-Id")
            if new_session_id:
                self.session_id = new_session_id
            
            # 202 Accepted — нормальный ответ для notifications
            if resp.status_code == 202:
                return {"jsonrpc": "2.0", "result": {}, "_accepted": True}
            
            if resp.status_code != 200:
                error_text = resp.text[:200] if resp.text else ""
                logger.error(f"MCP HTTP {resp.status_code}: {error_text}")
                return {"error": f"HTTP {resp.status_code}: {error_text}"}
            
            content_type = resp.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                return self._parse_sse_response(resp.text)
            else:
                try:
                    return resp.json()
                except json.JSONDecodeError:
                    return self._parse_sse_response(resp.text)
                    
        except requests.exceptions.Timeout:
            logger.error("MCP timeout")
            return {"error": "Timeout"}
        except Exception as e:
            logger.error(f"MCP request error: {e}")
            return {"error": str(e)}

    def initialize(self) -> bool:
        if self._initialized:
            return True
            
        init_payload = {
            "jsonrpc": "2.0", "id": "1", "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05", 
                "capabilities": {},
                "clientInfo": {"name": "tutu-travel-agent", "version": "2.0.0"}
            }
        }
        
        logger.info(f"MCP initialize на {self.url}...")
        result = self._post(init_payload, timeout=30)
        if "error" in result:
            logger.error(f"MCP Init Error: {result['error']}")
            return False
        
        logger.info("✅ MCP сессия установлена" + (f" (session: {self.session_id[:12]}...)" if self.session_id else " (stateless)"))
        
        notif_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self._post(notif_payload, timeout=15)
        logger.debug("MCP notifications/initialized отправлен")
        
        self._initialized = True
        logger.info("✅ MCP сессия инициализирована")
        return True

    def list_tools(self) -> List[Dict]:
        if not self._initialized:
            if not self.initialize():
                return []
        
        if self._tools_cache:
            return self._tools_cache
            
        payload = {"jsonrpc": "2.0", "id": "2", "method": "tools/list", "params": {}}
        result = self._post(payload, timeout=10)
        
        if "error" in result:
            logger.error(f"MCP tools/list failed: {result['error']}")
            return []
        
        tools_data = result.get("result", {}).get("tools", [])
        self._tools_cache = tools_data
        logger.info(f"📋 Получено {len(tools_data)} MCP-инструментов")
        return self._tools_cache

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        if not self._initialized:
            if not self.initialize():
                return "❌ MCP не инициализирован"
        
        payload = {
            "jsonrpc": "2.0", 
            "id": str(datetime.now().timestamp()),
            "method": "tools/call", 
            "params": {"name": tool_name, "arguments": arguments}
        }
        
        result = self._post(payload, timeout=120)
        
        if "error" in result:
            return f"❌ MCP Error: {result['error']}"
        
        content = result.get("result", {}).get("content", [])
        if content and isinstance(content[0], dict):
            return content[0].get("text", str(result))
        
        return str(result)

    def get_tools_as_functions(self) -> List[Callable]:
        """Динамически создаёт Python-функции для каждого MCP-инструмента."""
        tools_defs = self.list_tools()
        functions = []
        
        for t_def in tools_defs:
            name = t_def.get("name")
            desc = t_def.get("description", "MCP tool")
            input_schema = t_def.get("inputSchema", {})
            
            def make_wrapper(t_name, t_desc, t_schema):
                def wrapper(**kwargs):
                    clean_args = {k: v for k, v in kwargs.items() if v is not None}
                    return self.call_tool(t_name, clean_args)
                
                wrapper.__name__ = t_name
                wrapper.__doc__ = t_desc
                
                # Создаём аннотации
                properties = t_schema.get("properties", {})
                annotations = {}
                for prop_name, prop_def in properties.items():
                    p_type = prop_def.get("type", "string")
                    p_desc = prop_def.get("description", "")
                    type_map = {"string": str, "integer": int, "number": float, "boolean": bool, "array": list, "object": dict}
                    py_type = type_map.get(p_type, str)
                    
                    from typing import Annotated
                    annotations[prop_name] = Annotated[py_type, p_desc]
                
                wrapper.__annotations__ = annotations
                return wrapper
            
            func = make_wrapper(name, desc, input_schema)
            functions.append(func)
            
        return functions