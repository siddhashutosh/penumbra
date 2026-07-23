"""SQLite-backed cache + forecast read-model + pipeline runs (CON-4).

Single seam for a later move to managed storage (NFR-5 in KESSLER's sibling).
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS kv_cache (
  key TEXT PRIMARY KEY, payload TEXT NOT NULL,
  fetched_at TEXT NOT NULL, ttl_seconds INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS forecast_snapshots (
  id TEXT PRIMARY KEY, issued_at TEXT NOT NULL, document TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL,
  started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL,
  items INTEGER DEFAULT 0, error TEXT);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CacheService:
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._lock = threading.Lock()
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.executescript(_DDL)
            logger.info("Cache store ready at %s", db_path)
        except sqlite3.Error as exc:
            logger.error("Failed to initialise cache store: %s", exc)
            raise

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------- kv cache
    def get(self, key: str, *, allow_stale: bool = False) -> Any | None:
        try:
            with self._lock, self._connect() as conn:
                row = conn.execute(
                    "SELECT payload, fetched_at, ttl_seconds FROM kv_cache WHERE key=?",
                    (key,),
                ).fetchone()
        except sqlite3.Error as exc:
            logger.error("Cache read failed for %s: %s", key, exc)
            return None
        if row is None:
            return None
        age = (_now() - datetime.fromisoformat(row["fetched_at"])).total_seconds()
        if age > row["ttl_seconds"] and not allow_stale:
            return None
        try:
            return json.loads(row["payload"])
        except json.JSONDecodeError:
            return None

    def put(self, key: str, payload: Any, ttl_seconds: int) -> None:
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO kv_cache (key,payload,fetched_at,ttl_seconds) "
                    "VALUES (?,?,?,?)",
                    (key, json.dumps(payload, default=str), _now().isoformat(), ttl_seconds),
                )
        except sqlite3.Error as exc:
            logger.error("Cache write failed for %s: %s", key, exc)

    def get_or_fetch(self, key: str, ttl_seconds: int, loader: Callable[[], Any]) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        try:
            fresh = loader()
        except Exception as exc:
            stale = self.get(key, allow_stale=True)
            if stale is not None:
                logger.warning("Loader failed for %s (%s); serving stale", key, exc)
                return stale
            raise
        self.put(key, fresh, ttl_seconds)
        return fresh

    # ------------------------------------------------------- forecast model
    def save_snapshot(self, snapshot_id: str, document: dict) -> None:
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO forecast_snapshots (id,issued_at,document) "
                    "VALUES (?,?,?)",
                    (snapshot_id, _now().isoformat(), json.dumps(document, default=str)),
                )
        except sqlite3.Error as exc:
            logger.error("Snapshot save failed: %s", exc)

    def load_snapshot(self, snapshot_id: str) -> dict | None:
        try:
            with self._lock, self._connect() as conn:
                row = conn.execute(
                    "SELECT document FROM forecast_snapshots WHERE id=?", (snapshot_id,)
                ).fetchone()
            return json.loads(row["document"]) if row else None
        except (sqlite3.Error, json.JSONDecodeError):
            return None

    # -------------------------------------------------------- pipeline runs
    def record_run_start(self, agent: str) -> int:
        try:
            with self._lock, self._connect() as conn:
                cur = conn.execute(
                    "INSERT INTO pipeline_runs (agent,started_at,status) VALUES (?,?, 'running')",
                    (agent, _now().isoformat()),
                )
                return int(cur.lastrowid)
        except sqlite3.Error:
            return -1

    def record_run_finish(self, run_id: int, status: str, items: int,
                          error: str | None = None) -> None:
        if run_id < 0:
            return
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    "UPDATE pipeline_runs SET finished_at=?, status=?, items=?, error=? WHERE id=?",
                    (_now().isoformat(), status, items, error, run_id),
                )
        except sqlite3.Error:
            pass

    def latest_runs(self) -> dict[str, dict]:
        try:
            with self._lock, self._connect() as conn:
                rows = conn.execute(
                    "SELECT r.* FROM pipeline_runs r JOIN "
                    "(SELECT agent, MAX(id) AS mid FROM pipeline_runs GROUP BY agent) m "
                    "ON r.agent=m.agent AND r.id=m.mid"
                ).fetchall()
            return {r["agent"]: dict(r) for r in rows}
        except sqlite3.Error:
            return {}
