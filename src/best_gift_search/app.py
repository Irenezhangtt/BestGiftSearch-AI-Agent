from __future__ import annotations

import os
from collections import defaultdict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .agents import AgentLoop
from .memory import MemoryStore
from .models import AgentEvent, FeedbackRequest, SearchRequest, SearchResponse

app = FastAPI(title="Best Gift Search API", version="0.1.0", description="Explainable multi-agent gift discovery")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("BEST_GIFT_CORS", "http://localhost:5173")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
memory = MemoryStore()
loop = AgentLoop(memory)
connections: dict[str, set[WebSocket]] = defaultdict(set)


async def broadcast(event: AgentEvent):
    stale = []
    for socket in connections[event.thread_id]:
        try:
            await socket.send_json(event.model_dump())
        except Exception:
            stale.append(socket)
    for socket in stale:
        connections[event.thread_id].discard(socket)


@app.get("/health")
def health():
    return {"status": "ok", "service": "best-gift-search"}


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    return await loop.run(request, broadcast)


@app.get("/api/threads/{thread_id}")
def thread(thread_id: str):
    result = memory.get_thread(thread_id)
    if not result:
        raise HTTPException(404, "Thread not found")
    return result


@app.post("/api/threads/{thread_id}/feedback")
def feedback(thread_id: str, request: FeedbackRequest):
    memory.feedback(thread_id, request.product_id, request.value, request.note)
    return {"accepted": True}


@app.post("/api/threads/{thread_id}/cancel")
def cancel(thread_id: str):
    memory.cancel(thread_id)
    return {"cancelled": True}


@app.websocket("/ws/{thread_id}")
async def events(websocket: WebSocket, thread_id: str):
    await websocket.accept(); connections[thread_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections[thread_id].discard(websocket)
