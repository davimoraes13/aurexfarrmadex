"""Memory Engine (long-term). Busca por sobreposição de termos; embeddings/pgvector depois.
Nunca guarda credenciais como memória comum."""
from __future__ import annotations

import json
import re
import time

from backend.database.db import Database

_SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_\-]{16,}", r"AKIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{20,}",
    r"(?i)\b(password|senha|passwd|api[_-]?key|secret|token)\b\s*[:=]\s*\S+",
    r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}",
]


class SecretDetected(Exception):
    pass


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w{2,}", text.lower()))


class MemoryEngine:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, content: str, tags: list[str] | None = None, scope: str = "long_term") -> int:
        if any(re.search(p, content) for p in _SECRET_PATTERNS):
            raise SecretDetected("conteúdo parece conter credencial; use o cofre de segredos")
        cur = self.db.conn.execute(
            "INSERT INTO memories(scope, content, tags, created) VALUES (?,?,?,?)",
            (scope, content, json.dumps(tags or []), time.time()))
        self.db.conn.commit()
        return cur.lastrowid

    def search(self, query: str, limit: int = 5) -> list[dict]:
        q = _tokens(query)
        scored = []
        for r in self.db.conn.execute("SELECT * FROM memories"):
            score = len(q & (_tokens(r["content"]) | _tokens(r["tags"])))
            if score:
                scored.append((score, dict(r)))
        scored.sort(key=lambda x: (-x[0], -x[1]["created"]))
        return [d for _, d in scored[:limit]]

    def update(self, mid: int, content: str) -> bool:
        if any(re.search(p, content) for p in _SECRET_PATTERNS):
            raise SecretDetected("conteúdo parece conter credencial")
        cur = self.db.conn.execute("UPDATE memories SET content=? WHERE id=?", (content, mid))
        self.db.conn.commit()
        return cur.rowcount == 1

    def delete(self, mid: int) -> bool:
        cur = self.db.conn.execute("DELETE FROM memories WHERE id=?", (mid,))
        self.db.conn.commit()
        return cur.rowcount == 1

    def export(self) -> str:
        return json.dumps([dict(r) for r in self.db.conn.execute("SELECT * FROM memories")],
                          ensure_ascii=False)
