from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id          TEXT PRIMARY KEY,
    input_text      TEXT NOT NULL,
    context         TEXT,
    verdict         TEXT NOT NULL,
    staleness_score REAL NOT NULL,
    action          TEXT NOT NULL,
    claims_total    INTEGER NOT NULL,
    claims_stale    INTEGER NOT NULL,
    mode            TEXT NOT NULL,
    provider        TEXT NOT NULL,
    preview         TEXT NOT NULL,
    latency_ms      INTEGER NOT NULL,
    payload         TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);

CREATE TABLE IF NOT EXISTS cache (
    key        TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    expires_at REAL NOT NULL,
    created_at TEXT NOT NULL
);
"""


class Store:
    """SQLite-backed run history + verdict cache.

    Single-file SQLite keeps the free-tier deployment trivial (mount /data).
    The interface is small enough to swap for Turso/Postgres in v0.2.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def save_run(self, detail: dict) -> None:
        claims = detail.get("claims", [])
        stale = sum(1 for c in claims if c.get("verdict") == "stale")
        preview = (detail.get("input_text") or "").strip().replace("\n", " ")[:160]
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, input_text, context, verdict, staleness_score, action,
                    claims_total, claims_stale, mode, provider, preview, latency_ms,
                    payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    detail["run_id"],
                    detail.get("input_text", ""),
                    detail.get("context"),
                    detail["verdict"],
                    float(detail["staleness_score"]),
                    detail["action"],
                    len(claims),
                    stale,
                    detail["mode"],
                    detail["provider"],
                    preview,
                    int(detail.get("latency_ms", 0)),
                    json.dumps(detail, ensure_ascii=False, default=str),
                    detail["created_at"],
                ),
            )
            self._conn.commit()

    def get_run(self, run_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return json.loads(row["payload"]) if row else None

    def list_runs(self, limit: int = 25, offset: int = 0) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT run_id, verdict, staleness_score, action, claims_total,
                       claims_stale, mode, provider, preview, created_at
                FROM runs ORDER BY created_at DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def stats(self) -> dict:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT
                    COUNT(*) AS runs,
                    COALESCE(SUM(claims_total), 0) AS claims,
                    COALESCE(SUM(claims_stale), 0) AS stale_claims,
                    COALESCE(AVG(latency_ms), 0) AS avg_latency_ms
                FROM runs
                """
            ).fetchone()
        runs = int(row["runs"] or 0)
        claims = int(row["claims"] or 0)
        stale = int(row["stale_claims"] or 0)
        return {
            "runs": runs,
            "claims": claims,
            "stale_claims": stale,
            "stale_rate": (stale / claims) if claims else 0.0,
            "avg_latency_ms": float(row["avg_latency_ms"] or 0.0),
        }

    def get_cache(self, key: str) -> dict | None:
        now = time.time()
        with self._lock:
            row = self._conn.execute(
                "SELECT payload, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if not row:
                return None
            if row["expires_at"] < now:
                self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                self._conn.commit()
                return None
        return json.loads(row["payload"])

    def set_cache(self, key: str, payload: dict, ttl_seconds: int) -> None:
        expires = time.time() + max(1, ttl_seconds)
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO cache (key, payload, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (
                    key,
                    json.dumps(payload, ensure_ascii=False, default=str),
                    expires,
                    datetime.now(UTC).isoformat(),
                ),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
