"""Persistência (SQLite, stdlib). Desenvolvimento local; PostgreSQL+pgvector entram depois
com a mesma interface. Missões e memória persistem aqui."""
from __future__ import annotations

import json
import sqlite3

from backend.core.mission import Mission, MissionState


class Database:
    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS missions(
            id TEXT PRIMARY KEY, objective TEXT NOT NULL, priority INTEGER, state TEXT NOT NULL,
            history TEXT NOT NULL, paused_from TEXT, transitions INTEGER, replans INTEGER,
            max_transitions INTEGER, max_replans INTEGER);
        CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT NOT NULL, content TEXT NOT NULL,
            tags TEXT NOT NULL, created REAL NOT NULL);
        """)

    def save_mission(self, m: Mission) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO missions VALUES (?,?,?,?,?,?,?,?,?,?)",
            (m.id, m.objective, m.priority, m.state.value, json.dumps(m.history),
             m._paused_from.value if m._paused_from else None, m._transitions, m._replans,
             m.max_transitions, m.max_replans))
        self.conn.commit()

    def load_mission(self, mid: str) -> Mission | None:
        r = self.conn.execute("SELECT * FROM missions WHERE id=?", (mid,)).fetchone()
        if r is None:
            return None
        m = Mission(objective=r["objective"], priority=r["priority"], id=r["id"],
                    max_transitions=r["max_transitions"], max_replans=r["max_replans"])
        m.state = MissionState(r["state"])
        m.history = json.loads(r["history"])
        m._paused_from = MissionState(r["paused_from"]) if r["paused_from"] else None
        m._transitions, m._replans = r["transitions"], r["replans"]
        return m

    def list_missions(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT id, objective, state FROM missions")]
