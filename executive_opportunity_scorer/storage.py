from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "pipeline.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                fit_score INTEGER,
                risk_score INTEGER,
                confidence INTEGER,
                recommendation TEXT,
                timing_window TEXT,
                approach_angle TEXT,
                result_json TEXT NOT NULL,
                input_json TEXT,
                created_at TEXT NOT NULL
            )
        """)


def save_result(result: dict[str, Any], input_data: dict[str, Any] | None = None) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO pipeline
                (company_name, snapshot_date, fit_score, risk_score, confidence,
                 recommendation, timing_window, approach_angle, result_json, input_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.get("company_name", ""),
                result.get("snapshot_date", ""),
                result.get("fit_score"),
                result.get("risk_score"),
                result.get("confidence"),
                result.get("recommendation", ""),
                result.get("timing_window", ""),
                result.get("approach_angle", ""),
                json.dumps(result),
                json.dumps(input_data) if input_data is not None else None,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return cursor.lastrowid


def list_pipeline() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, company_name, snapshot_date, fit_score, risk_score, confidence,
                   recommendation, timing_window, approach_angle, created_at
            FROM pipeline
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_entry(entry_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM pipeline WHERE id = ?", (entry_id,)).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["result"] = json.loads(data.pop("result_json"))
        raw_input = data.pop("input_json", None)
        data["input"] = json.loads(raw_input) if raw_input else None
        return data


def delete_entry(entry_id: int) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM pipeline WHERE id = ?", (entry_id,))
        return cursor.rowcount > 0
