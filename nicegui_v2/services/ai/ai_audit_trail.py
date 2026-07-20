from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parents[3] / "ideas.db"


def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_ai_action_tables() -> None:
    conn = _conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_action_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            user_id INTEGER,
            user_key TEXT,
            intent TEXT,
            action_name TEXT,
            prompt_original TEXT,
            proposal_json TEXT,
            execution_json TEXT,
            status TEXT,
            error_text TEXT,
            confirmed_by_user INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_ai_action_log_company ON ai_action_log(company_id, id DESC)")
    conn.commit()
    conn.close()


def write_ai_action_log(
    *,
    company_id: int,
    user_id: int | None,
    user_key: str,
    intent: str,
    action_name: str,
    prompt_original: str,
    proposal: dict[str, Any] | None,
    execution: dict[str, Any] | None,
    status: str,
    error_text: str = "",
    confirmed_by_user: bool = False,
) -> None:
    ensure_ai_action_tables()
    conn = _conn()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO ai_action_log (
            company_id, user_id, user_key, intent, action_name, prompt_original,
            proposal_json, execution_json, status, error_text, confirmed_by_user, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(company_id),
            int(user_id) if user_id else None,
            str(user_key or ""),
            str(intent or ""),
            str(action_name or ""),
            str(prompt_original or ""),
            json.dumps(proposal or {}, ensure_ascii=False),
            json.dumps(execution or {}, ensure_ascii=False),
            str(status or ""),
            str(error_text or ""),
            1 if confirmed_by_user else 0,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def list_ai_action_logs(company_id: int, limit: int = 80) -> list[dict[str, Any]]:
    ensure_ai_action_tables()
    conn = _conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, company_id, user_id, user_key, intent, action_name, prompt_original, proposal_json, execution_json,
               status, error_text, confirmed_by_user, created_at
        FROM ai_action_log
        WHERE company_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (int(company_id), max(1, int(limit))),
    )
    rows = c.fetchall()
    conn.close()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        for key in ("proposal_json", "execution_json"):
            raw = str(item.get(key) or "")
            try:
                item[key] = json.loads(raw) if raw else {}
            except Exception:
                item[key] = {}
        result.append(item)
    return result
