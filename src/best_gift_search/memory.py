from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager

from .models import AgentEvent, JobStatus, SearchResponse


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
                CREATE TABLE IF NOT EXISTS threads (id TEXT PRIMARY KEY, user_id TEXT DEFAULT 'anonymous', intent TEXT, response TEXT, cancelled INTEGER DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, thread_id TEXT, payload TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, thread_id TEXT, product_id TEXT, value INTEGER, note TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS checkpoints (id INTEGER PRIMARY KEY, thread_id TEXT, phase TEXT, state TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, thread_id TEXT, status TEXT, payload TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
            """)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(threads)")}
            if "user_id" not in columns:
                db.execute("ALTER TABLE threads ADD COLUMN user_id TEXT DEFAULT 'anonymous'")
            db.execute("UPDATE jobs SET status='failed', payload=json_set(COALESCE(payload,'{}'),'$.error','Process restarted before completion') WHERE status IN ('queued','running')")

    def save_event(self, event: AgentEvent):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO events(id, thread_id, payload) VALUES(?,?,?)", (event.id, event.thread_id, event.model_dump_json()))

    def save_response(self, response: SearchResponse):
        with self.connect() as db:
            db.execute("INSERT INTO threads(id,intent,response,cancelled) VALUES(?,?,?,0) ON CONFLICT(id) DO UPDATE SET intent=excluded.intent,response=excluded.response,cancelled=0,updated_at=CURRENT_TIMESTAMP", (response.thread_id, response.intent.model_dump_json(), response.model_dump_json()))

    def begin_thread(self, thread_id: str, user_id: str = "anonymous"):
        with self.connect() as db:
            db.execute("INSERT INTO threads(id,user_id,cancelled) VALUES(?,?,0) ON CONFLICT(id) DO UPDATE SET user_id=excluded.user_id,cancelled=0,updated_at=CURRENT_TIMESTAMP", (thread_id, user_id))

    def checkpoint(self, thread_id: str, phase: str, state: dict):
        compact = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
        with self.connect() as db:
            db.execute("INSERT INTO checkpoints(thread_id,phase,state) VALUES(?,?,?)", (thread_id, phase, compact))

    def is_cancelled(self, thread_id: str) -> bool:
        with self.connect() as db:
            row = db.execute("SELECT cancelled FROM threads WHERE id=?", (thread_id,)).fetchone()
        return bool(row and row["cancelled"])

    def events(self, thread_id: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM events WHERE thread_id=? ORDER BY created_at,id", (thread_id,)).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def compact_context(self, thread_id: str, max_events: int = 20) -> dict:
        with self.connect() as db:
            checkpoint = db.execute("SELECT phase,state,created_at FROM checkpoints WHERE thread_id=? ORDER BY id DESC LIMIT 1", (thread_id,)).fetchone()
            rows = db.execute("SELECT payload FROM events WHERE thread_id=? ORDER BY created_at DESC,id DESC LIMIT ?", (thread_id, max_events)).fetchall()
        return {"checkpoint": ({"phase": checkpoint["phase"], "state": json.loads(checkpoint["state"]), "created_at": checkpoint["created_at"]} if checkpoint else None), "recent_events": [json.loads(row["payload"]) for row in reversed(rows)]}

    def save_job(self, job: JobStatus):
        with self.connect() as db:
            db.execute("INSERT INTO jobs(id,thread_id,status,payload) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,payload=excluded.payload,updated_at=CURRENT_TIMESTAMP", (job.id, job.thread_id, job.status, job.model_dump_json()))

    def get_job(self, job_id: str) -> JobStatus | None:
        with self.connect() as db:
            row = db.execute("SELECT payload,status,thread_id FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row: return None
        payload = json.loads(row["payload"] or "{}")
        payload.update({"id": job_id, "thread_id": row["thread_id"], "status": row["status"]})
        return JobStatus.model_validate(payload)

    def get_thread(self, thread_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT response,cancelled FROM threads WHERE id=?", (thread_id,)).fetchone()
            return ({"response": json.loads(row["response"]), "cancelled": bool(row["cancelled"])} if row and row["response"] else None)

    def preferences(self, thread_id: str, user_id: str = "anonymous") -> list[str]:
        with self.connect() as db:
            rows = db.execute("SELECT DISTINCT f.product_id FROM feedback f LEFT JOIN threads t ON t.id=f.thread_id WHERE f.value=1 AND (f.thread_id=? OR (? <> 'anonymous' AND t.user_id=?))", (thread_id, user_id, user_id)).fetchall()
        return [row["product_id"].replace("-", " ") for row in rows]

    def feedback(self, thread_id: str, product_id: str, value: int, note: str | None):
        with self.connect() as db:
            db.execute("INSERT INTO feedback(thread_id,product_id,value,note) VALUES(?,?,?,?)", (thread_id, product_id, value, note))

    def cancel(self, thread_id: str):
        with self.connect() as db:
            db.execute("UPDATE threads SET cancelled=1 WHERE id=?", (thread_id,))
