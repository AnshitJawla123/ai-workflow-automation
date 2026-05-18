"""SQLite-backed key/value cache (zero external infra)."""
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Optional

from ..core.config import settings


class KVCache:
    def __init__(self, path: Optional[str] = None):
        self.path = path or str(Path(settings.data_dir) / "cache.db")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        c.execute("PRAGMA journal_mode=WAL;")
        return c

    def _init(self):
        with self._lock, self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS kv ("
                " k TEXT PRIMARY KEY, v TEXT, expires_at REAL)"
            )

    def _ensure_table(self, c):
        c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT, expires_at REAL)")

    def get(self, key: str) -> Optional[Any]:
        with self._lock, self._conn() as c:
            self._ensure_table(c)
            row = c.execute("SELECT v, expires_at FROM kv WHERE k=?", (key,)).fetchone()
        if not row:
            return None
        v, exp = row
        if exp and exp < time.time():
            self.delete(key)
            return None
        try:
            return json.loads(v)
        except Exception:
            return v

    def set(self, key: str, value: Any, ttl_sec: Optional[int] = None) -> None:
        exp = time.time() + ttl_sec if ttl_sec else None
        with self._lock, self._conn() as c:
            self._ensure_table(c)
            c.execute(
                "INSERT OR REPLACE INTO kv(k,v,expires_at) VALUES(?,?,?)",
                (key, json.dumps(value, default=str), exp),
            )

    def delete(self, key: str) -> None:
        with self._lock, self._conn() as c:
            c.execute("DELETE FROM kv WHERE k=?", (key,))


cache = KVCache()
