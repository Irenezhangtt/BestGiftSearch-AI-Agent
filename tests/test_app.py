from pathlib import Path

from fastapi.testclient import TestClient

from best_gift_search import app as app_module
from best_gift_search.agents import AgentLoop
from best_gift_search.memory import MemoryStore


def test_health():
    assert TestClient(app_module.app).get("/health").json()["status"] == "ok"


def test_search_returns_ranked_affordable_gifts(tmp_path: Path):
    app_module.memory = MemoryStore(str(tmp_path / "test.db"))
    app_module.loop = AgentLoop(app_module.memory)
    response = TestClient(app_module.app).post("/api/search", json={"message": "Birthday gift for my sister who loves coffee and travel under $80", "country": "US"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"]["budget"] == 80
    assert body["recommendations"][0]["product"]["id"] == "coffee-kit"
    assert body["events"][-1]["phase"] == "complete"
    assert body["evaluation"]["overall"] > 0
    assert app_module.memory.events(body["thread_id"])


def test_feedback_is_persisted(tmp_path: Path):
    store = MemoryStore(str(tmp_path / "feedback.db"))
    store.feedback("thread", "coffee-kit", 1, "Great")
    assert store.preferences("thread") == ["coffee kit"]


def test_cancel_state_and_checkpoint(tmp_path: Path):
    store = MemoryStore(str(tmp_path / "state.db"))
    store.begin_thread("thread")
    store.checkpoint("thread", "intent", {"budget": 50})
    assert not store.is_cancelled("thread")
    store.cancel("thread")
    assert store.is_cancelled("thread")
