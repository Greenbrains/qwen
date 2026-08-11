"""
Долгосрочная память пользователей (SQLite, stdlib).
Профиль пользователя = alias + кодовое слово + накопленные маркеры.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


class MemoryStore:
    """Хранилище маркеров и профилей пользователей."""

    def __init__(self, db_path: str = "data/memory.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    # ------------------------------------------------------------------
    # Схема
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id              INTEGER PRIMARY KEY,
                    alias           TEXT UNIQUE NOT NULL,
                    passphrase_hash TEXT NOT NULL,
                    created_at      REAL NOT NULL,
                    last_seen       REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id         INTEGER PRIMARY KEY,
                    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at REAL NOT NULL,
                    kind       TEXT NOT NULL DEFAULT 'marker',
                    content    TEXT NOT NULL,
                    meta       TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_mem_user
                    ON memories(user_id, created_at DESC);
            """)

    # ------------------------------------------------------------------
    # Идентификация
    # ------------------------------------------------------------------
    @staticmethod
    def _hash(alias: str, passphrase: str) -> str:
        return hashlib.sha256(
            f"{alias.lower()}::{passphrase}".encode("utf-8")
        ).hexdigest()

    def exists(self, alias: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM users WHERE alias = ?", (alias.lower(),)
            ).fetchone()
        return row is not None

    def register(self, alias: str, passphrase: str) -> None:
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO users(alias, passphrase_hash, created_at, last_seen) "
                "VALUES (?,?,?,?)",
                (alias.lower(), self._hash(alias, passphrase), now, now),
            )

    def verify(self, alias: str, passphrase: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT passphrase_hash FROM users WHERE alias = ?", (alias.lower(),)
            ).fetchone()
        if row is None:
            return False
        ok = row["passphrase_hash"] == self._hash(alias, passphrase)
        if ok:
            with self._lock, self._conn:
                self._conn.execute(
                    "UPDATE users SET last_seen = ? WHERE alias = ?",
                    (time.time(), alias.lower()),
                )
        return ok

    # ------------------------------------------------------------------
    # Маркеры
    # ------------------------------------------------------------------
    def add_marker(
        self, alias: str, content: str, meta: Optional[Dict[str, Any]] = None
    ) -> None:
        with self._lock, self._conn:
            user = self._conn.execute(
                "SELECT id FROM users WHERE alias = ?", (alias.lower(),)
            ).fetchone()
            if user is None:
                return
            self._conn.execute(
                "INSERT INTO memories(user_id, created_at, kind, content, meta) "
                "VALUES (?,?,?,?,?)",
                (
                    user["id"],
                    time.time(),
                    "marker",
                    content,
                    json.dumps(meta or {}, ensure_ascii=False),
                ),
            )

    def get_markers(self, alias: str, limit: int = 10) -> List[str]:
        """Последние маркеры, от старых к новым (для вставки в историю)."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT m.content FROM memories m
                JOIN users u ON u.id = m.user_id
                WHERE u.alias = ? AND m.kind = 'marker'
                ORDER BY m.created_at DESC LIMIT ?
                """,
                (alias.lower(), limit),
            ).fetchall()
        return [r["content"] for r in reversed(rows)]

    def forget(self, alias: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM users WHERE alias = ?", (alias.lower(),))

    def close(self) -> None:
        with self._lock:
            self._conn.close()