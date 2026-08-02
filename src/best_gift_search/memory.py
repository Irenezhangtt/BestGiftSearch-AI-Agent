from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager

from .models import AgentEvent, SearchIntent, SearchResponse


class MemoryStore:
    def __init__(self, path: str | None = None):
        self.path = path or os.getenv("BEST_GIFT_DB", "best_gift_search.db")
        self._initialize()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self):
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS threads (id TEXT PRIMARY KEY, intent TEXT, response TEXT, cancelled INTEGER DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, thread_id TEXT, payload TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, thread_id TEXT, product_id TEXT, value INTEGER, note TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            """)

    def save_event(self, event: AgentEvent):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO events(id, thread_id, payload) VALUES(?,?,?)", (event.id, event.thread_id, event.model_dump_json()))

    def save_response(self, response: SearchResponse):
        with self.connect() as db:
            db.execute("INSERT INTO threads(id,intent,response,cancelled) VALUES(?,?,?,0) ON CONFLICT(id) DO UPDATE SET intent=excluded.intent,response=excluded.response,cancelled=0,updated_at=CURRENT_TIMESTAMP", (response.thread_id, response.intent.model_dump_json(), response.model_dump_json()))

    def get_thread(self, thread_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT response,cancelled FROM threads WHERE id=?", (thread_id,)).fetchone()
            return ({"response": json.loads(row["response"]), "cancelled": bool(row["cancelled"])} if row and row["response"] else None)

    def preferences(self, thread_id: str) -> list[str]:
        with self.connect() as db:
            rows = db.execute("SELECT product_id FROM feedback WHERE thread_id=? AND value=1", (thread_id,)).fetchall()
        return [row["product_id"].replace("-", " ") for row in rows]

    def feedback(self, thread_id: str, product_id: str, value: int, note: str | None):
        with self.connect() as db:
            db.execute("INSERT INTO feedback(thread_id,product_id,value,note) VALUES(?,?,?,?)", (thread_id, product_id, value, note))

    def cancel(self, thread_id: str):
        with self.connect() as db:
            db.execute("UPDATE threads SET cancelled=1 WHERE id=?", (thread_id,))
