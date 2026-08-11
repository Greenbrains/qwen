"""
Управление состоянием сессии.
Класс Session хранит историю сообщений, переменные промпта и текущее состояние.
Используется как контейнер для агента, чтобы обеспечить контекстность диалога.

Добавлено (пункт 1.3 — компрессия истории):
- compact(): старые ходы заменяются маркерами, сырые role:tool удаляются.
  Последние N ходов сохраняются целиком (для details_ref / checkout_ref).
- user_alias: идентификатор пользователя для долгосрочной памяти.
- compact_messages(): модульная функция, пригодная для вызова из оркестратора.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

_MARKER_PREFIX = "📜 [ИСТОРИЯ]"
_TRUNC_MARK = "\n\n…["  # хвост, который BaseAgent добавляет при усечении


# ======================================================================
# Вспомогательные функции компактизации
# ======================================================================
def _split_turns(messages: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Разбивает историю на ходы: [user, assistant(tool_calls), tool, ..., assistant(final)]."""
    turns: List[List[Dict[str, Any]]] = []
    head: List[Dict[str, Any]] = []  # всё до первого user (обычно пусто)
    current: Optional[List[Dict[str, Any]]] = None
    for msg in messages:
        if msg.get("role") == "user" and not str(msg.get("content", "")).startswith(_MARKER_PREFIX):
            if current is not None:
                turns.append(current)
            elif head:
                turns.append(head)
                head = []
            current = [msg]
        else:
            (current if current is not None else head).append(msg)
    if current is not None:
        turns.append(current)
    elif head:
        turns.append(head)
    return turns


def _extract_facts(tool_name: str, args: Dict[str, Any], payload: Any) -> Optional[str]:
    """Достаёт из JSON-ответа компактные факты: сколько вариантов и от какой цены."""
    if not isinstance(payload, dict):
        return None
    items = payload.get("offers") or payload.get("hotels") or payload.get("variants")
    if not isinstance(items, list) or not items:
        return None

    prices: List[float] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        p = it.get("price")
        if isinstance(p, dict) and isinstance(p.get("amount"), (int, float)):
            prices.append(p["amount"])
        else:
            # hotels: best_offer.price.amount
            bo = it.get("best_offer")
            if isinstance(bo, dict):
                bp = bo.get("price")
                if isinstance(bp, dict) and isinstance(bp.get("amount"), (int, float)):
                    prices.append(bp["amount"])

    route = args.get("origin") or args.get("city_name") or ""
    dest = args.get("destination") or ""
    date = args.get("departure_date") or args.get("check_in") or ""
    where = f"{route}→{dest}" if dest else str(route)

    parts: List[str] = []
    if where and date:
        parts.append(f"{tool_name}({where}, {date})")
    elif where:
        parts.append(f"{tool_name}({where})")
    else:
        parts.append(tool_name)
    parts.append(f"{len(items)} вариантов")
    if prices:
        parts.append(f"цена от {min(prices):.0f} ₽")
    return ", ".join(parts)


def _turn_to_marker(turn: List[Dict[str, Any]]) -> Optional[str]:
    """Превращает один завершённый ход в строку-маркер."""
    user_text = ""
    final_text = ""
    calls: Dict[str, tuple] = {}  # tool_call_id -> (name, args)
    facts: List[str] = []

    for msg in turn:
        role = msg.get("role")
        if role == "user" and not user_text:
            user_text = str(msg.get("content", ""))[:120]
        elif role == "assistant":
            for tc in msg.get("tool_calls") or []:
                fn = tc.get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except (json.JSONDecodeError, TypeError):
                    args = {}
                calls[tc.get("id", "")] = (fn.get("name", "?"), args)
            if not msg.get("tool_calls"):
                final_text = str(msg.get("content", ""))
        elif role == "tool":
            name, args = calls.get(msg.get("tool_call_id", ""), ("?", {}))
            # плейбуки в память не пишем
            if name.startswith("get_") and name.endswith("_instructions"):
                continue
            raw = str(msg.get("content", "")).split(_TRUNC_MARK)[0]
            try:
                fact = _extract_facts(name, args, json.loads(raw))
            except (json.JSONDecodeError, TypeError):
                fact = None
            if fact:
                facts.append(fact)

    if not user_text:
        return None
    parts = [f"{_MARKER_PREFIX} Запрос «{user_text}»"]
    if facts:
        parts.append("; ".join(facts))
    if final_text.strip():
        snippet = re.sub(r"\s+", " ", final_text).strip()
        parts.append(f"Итог: {snippet[:180]}…")
    return " | ".join(parts)


def compact_messages(
    messages: List[Dict[str, Any]], keep_last_turns: int = 2
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Модульная функция компактизации.
    Возвращает (compacted_messages, new_markers).
    """
    # 1. Извлекаем существующие маркеры (чтобы не потерять при повторной компактизации)
    existing_markers: List[Dict[str, Any]] = []
    working: List[Dict[str, Any]] = []
    for m in messages:
        if (
            m.get("role") == "assistant"
            and str(m.get("content", "")).startswith(_MARKER_PREFIX)
        ):
            existing_markers.append(m)
        else:
            working.append(m)

    # 2. Разделяем на ходы
    turns = _split_turns(working)
    if len(turns) <= keep_last_turns:
        return messages, []

    old, keep = turns[:-keep_last_turns], turns[-keep_last_turns:]

    # 3. Компактизация старых ходов
    new_marker_msgs: List[Dict[str, Any]] = []
    new_marker_texts: List[str] = []
    for turn in old:
        marker = _turn_to_marker(turn)
        if marker:
            new_marker_texts.append(marker)
            new_marker_msgs.append({"role": "assistant", "content": marker})

    # 4. Собираем: маркеры + компактированные ходы + последние ходы целиком
    compacted: List[Dict[str, Any]] = existing_markers + new_marker_msgs
    for turn in keep:
        compacted.extend(turn)

    # 5. Схлопываем дубли user-сообщений подряд (баг из логов)
    deduped: List[Dict[str, Any]] = []
    for msg in compacted:
        if (
            deduped
            and msg.get("role") == "user" == deduped[-1].get("role")
            and msg.get("content") == deduped[-1].get("content")
        ):
            continue
        deduped.append(msg)

    return deduped, new_marker_texts


# ======================================================================
# Session
# ======================================================================
class Session:
    """Контейнер состояния диалога."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or uuid.uuid4().hex
        self.messages: List[Dict[str, Any]] = []
        self.prompt_variables: Dict[str, Any] = {}
        self.last_tool_calls: List[Dict[str, Any]] = []
        self.user_alias: Optional[str] = None  # идентификатор пользователя («енот»)
        self.created_at: float = time.time()
        self.updated_at: float = time.time()

    # ------------------------------------------------------------------
    # История
    # ------------------------------------------------------------------
    def add_message(self, role: str, content: str, **extra) -> None:
        msg = {"role": role, "content": content}
        msg.update(extra)
        self.messages.append(msg)
        self.updated_at = time.time()

    def add_user(self, content: str) -> None:
        self.add_message("user", content)

    def add_assistant(self, content: str) -> None:
        self.add_message("assistant", content)

    def clear(self) -> None:
        self.messages = []
        self.last_tool_calls = []
        self.updated_at = time.time()

    @property
    def history(self) -> List[Dict[str, Any]]:
        return self.messages

    # ------------------------------------------------------------------
    # Компактизация (пункт 1.3)
    # ------------------------------------------------------------------
    def compact(self, keep_last_turns: int = 2) -> List[str]:
        """
        Сжимает историю: ходы старше keep_last_turns заменяются маркерами,
        сырые role:tool удаляются. Возвращает созданные маркеры.
        """
        compacted, markers = compact_messages(self.messages, keep_last_turns)
        self.messages = compacted
        self.updated_at = time.time()
        return markers

    # ------------------------------------------------------------------
    # Переменные промпта
    # ------------------------------------------------------------------
    def set_variable(self, key: str, value: Any) -> None:
        self.prompt_variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        return self.prompt_variables.get(key, default)

    # ------------------------------------------------------------------
    # Tool calls
    # ------------------------------------------------------------------
    def record_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> None:
        if tool_calls:
            self.last_tool_calls = tool_calls

    # ------------------------------------------------------------------
    # Сериализация
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "prompt_variables": self.prompt_variables,
            "last_tool_calls": self.last_tool_calls,
            "user_alias": self.user_alias,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        session = cls(session_id=data.get("session_id"))
        session.messages = data.get("messages", [])
        session.prompt_variables = data.get("prompt_variables", {})
        session.last_tool_calls = data.get("last_tool_calls", [])
        session.user_alias = data.get("user_alias")
        session.created_at = data.get("created_at", time.time())
        session.updated_at = data.get("updated_at", time.time())
        return session


# ======================================================================
# SessionStore
# ======================================================================
class SessionStore:
    """Простое in-memory хранилище сессий (для FastAPI)."""

    def __init__(self, ttl_seconds: int = 3600):
        self._sessions: Dict[str, Session] = {}
        self._ttl = ttl_seconds

    def _is_expired(self, session: Session) -> bool:
        return time.time() - session.updated_at >= self._ttl

    def cleanup(self) -> int:
        """Удаляет просроченные сессии. Возвращает число удалённых."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.updated_at >= self._ttl
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    def get_or_create(self, session_id: Optional[str] = None) -> Session:
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            if not self._is_expired(session):
                return session
            else:
                del self._sessions[session_id]
        session = Session(session_id=session_id)
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def save(self, session: Session) -> None:
        self._sessions[session.session_id] = session

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def clear(self) -> None:
        self._sessions.clear()
        