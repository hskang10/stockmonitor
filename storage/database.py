from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from config.settings import settings


def _resolve_db_path() -> Path:
    path = Path(settings.db_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_resolve_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS macro_cache (
                cache_key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS cpi_releases (
                reference_month TEXT PRIMARY KEY,
                headline_index REAL NOT NULL,
                headline_mom REAL NOT NULL,
                headline_yoy REAL NOT NULL,
                core_index REAL NOT NULL,
                core_mom REAL NOT NULL,
                core_yoy REAL NOT NULL,
                headline_mom_consensus REAL,
                headline_yoy_consensus REAL,
                core_mom_consensus REAL,
                core_yoy_consensus REAL,
                classification TEXT NOT NULL,
                multiplier REAL NOT NULL,
                delay_sessions INTEGER NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS cycle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                stage TEXT NOT NULL,
                event_date TEXT NOT NULL,
                note TEXT,
                UNIQUE(symbol, stage, event_date)
            );
            """
        )


def get_cache(cache_key: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT payload_json FROM macro_cache WHERE cache_key = ?", (cache_key,)
        ).fetchone()
    return json.loads(row["payload_json"]) if row else None


def set_cache(cache_key: str, payload: dict[str, Any]) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO macro_cache(cache_key, payload_json, fetched_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(cache_key) DO UPDATE SET
                payload_json = excluded.payload_json,
                fetched_at = CURRENT_TIMESTAMP
            """,
            (cache_key, json.dumps(payload, ensure_ascii=False)),
        )


def save_cpi_release(record: dict[str, Any]) -> None:
    columns = [
        "reference_month", "headline_index", "headline_mom", "headline_yoy",
        "core_index", "core_mom", "core_yoy", "headline_mom_consensus",
        "headline_yoy_consensus", "core_mom_consensus", "core_yoy_consensus",
        "classification", "multiplier", "delay_sessions", "source"
    ]
    values = [record.get(c) for c in columns]
    placeholders = ",".join("?" for _ in columns)
    update = ",".join(f"{c}=excluded.{c}" for c in columns[1:])
    with connection() as conn:
        conn.execute(
            f"INSERT INTO cpi_releases ({','.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT(reference_month) DO UPDATE SET {update}",
            values,
        )


def latest_cpi_release() -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM cpi_releases ORDER BY reference_month DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None
