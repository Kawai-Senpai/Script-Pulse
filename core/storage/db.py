from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_DIR = ROOT_DIR / ".tmp"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "scriptanalysis.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column in columns:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                raw_text TEXT,
                status TEXT,
                regeneration_prompt TEXT,
                last_report_json TEXT,
                last_validation_json TEXT,
                last_engagement_json TEXT,
                last_beat_json TEXT,
                last_emotion_json TEXT,
                last_improvement_json TEXT,
                last_token_usage_json TEXT,
                iterations INTEGER,
                tokens_used INTEGER,
                last_error TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_config (
                session_id TEXT PRIMARY KEY,
                config_json TEXT,
                updated_at TEXT
            )
            """
        )
        _ensure_column(conn, "sessions", "last_token_usage_json", "TEXT")
        conn.commit()
    finally:
        conn.close()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def create_session(title: Optional[str] = None) -> str:
    session_id = uuid.uuid4().hex
    now = _utc_now()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO sessions (
                session_id, title, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, title, "idle", now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return session_id


def upsert_input(session_id: str, title: Optional[str], raw_text: str) -> None:
    now = _utc_now()
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE sessions
            SET title = ?, raw_text = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (title, raw_text, now, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_regeneration_prompt(session_id: str, prompt: Optional[str]) -> None:
    now = _utc_now()
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE sessions
            SET regeneration_prompt = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (prompt, now, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_status(session_id: str, status: str) -> None:
    now = _utc_now()
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE sessions
            SET status = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (status, now, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def save_run_result(session_id: str, payload: Dict[str, Any]) -> None:
    now = _utc_now()
    validation = payload.get("validation") or {}
    status = "review" if validation.get("valid") is False else "complete"
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE sessions
            SET status = ?,
                last_report_json = ?,
                last_validation_json = ?,
                last_engagement_json = ?,
                last_beat_json = ?,
                last_emotion_json = ?,
                last_improvement_json = ?,
                last_token_usage_json = ?,
                iterations = ?,
                tokens_used = ?,
                last_error = ?,
                updated_at = ?
            WHERE session_id = ?
            """,
            (
                status,
                json.dumps(payload.get("report"), ensure_ascii=True),
                json.dumps(payload.get("validation"), ensure_ascii=True),
                json.dumps(payload.get("engagement_analysis"), ensure_ascii=True),
                json.dumps(payload.get("beat_extraction"), ensure_ascii=True),
                json.dumps(payload.get("emotion_analysis"), ensure_ascii=True),
                json.dumps(payload.get("improvement_plan"), ensure_ascii=True),
                json.dumps(payload.get("token_usage"), ensure_ascii=True),
                payload.get("iterations"),
                payload.get("tokens_used"),
                None,
                now,
                session_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def save_run_error(session_id: str, message: str) -> None:
    now = _utc_now()
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE sessions
            SET status = ?, last_error = ?, updated_at = ?
            WHERE session_id = ?
            """,
            ("error", message, now, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def delete_session(session_id: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        conn.execute(
            "DELETE FROM session_config WHERE session_id = ?",
            (session_id,),
        )
        conn.commit()
    finally:
        conn.close()


def list_sessions(limit: int = 50) -> list[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT session_id, title, raw_text, status, updated_at
            FROM sessions
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def set_config(session_id: str, config: Dict[str, Any]) -> None:
    now = _utc_now()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO session_config (session_id, config_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                config_json = excluded.config_json,
                updated_at = excluded.updated_at
            """,
            (session_id, json.dumps(config, ensure_ascii=True), now),
        )
        conn.commit()
    finally:
        conn.close()


def get_config(session_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT config_json FROM session_config WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row or not row[0]:
            return None
        return json.loads(row[0])
    finally:
        conn.close()
