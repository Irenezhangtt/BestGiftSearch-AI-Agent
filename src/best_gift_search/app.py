from __future__ import annotations

from collections import defaultdict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .agents import SearchCancelled
from .hooks import MetricsHook
from .guardrails import UnsafeInput
from .jobs import JobManager
from .memory import MemoryStore
from .models import AgentEvent, FeedbackRequest, JobStatus, SearchRequest, SearchResponse
from .middleware import ProductionMiddleware
from .runtime import build_agent_loop, runtime_info
from .settings import Settings

app = FastAPI(title="Best Gift Search API", version="0.1.0", description="Explainable multi-agent gift discovery")
settings = Settings.from_env()
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(ProductionMiddleware, api_key=settings.api_key, rate_limit_per_minute=settings.rate_limit_per_minute)
memory = MemoryStore()
metrics = MetricsHook()
loop = build_agent_loop(memory, hooks=[metrics])
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


jobs = JobManager(loop, broadcast)


@app.get("/", include_in_schema=False)
def index():
    return {
        "name": "Best Gift Search API",
        "status": "ready",
        "docs": "/docs",
        "health": "/health",
        "demo": "https://irenezhangtt.github.io/BestGiftSearch-AI-Agent/",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "best-gift-search", **runtime_info(loop)}


@app.get("/api/metrics")
def get_metrics():
    return metrics.snapshot()


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    try:
        return await loop.run(request, broadcast)
    except SearchCancelled:
        raise HTTPException(409, "Search cancelled")
    except UnsafeInput as error:
        raise HTTPException(422, str(error))


@app.post("/api/jobs", response_model=JobStatus, status_code=202)
async def create_job(request: SearchRequest):
    return jobs.submit(request)


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job: raise HTTPException(404, "Job not found")
    return job


@app.delete("/api/jobs/{job_id}", response_model=JobStatus)
def cancel_job(job_id: str):
    job = jobs.get(job_id)
    if not job: raise HTTPException(404, "Job not found")
    jobs.cancel(job_id)
    return jobs.get(job_id) or job


@app.get("/api/threads/{thread_id}")
def thread(thread_id: str):
    result = memory.get_thread(thread_id)
    if not result:
        raise HTTPException(404, "Thread not found")
    return result


@app.get("/api/threads/{thread_id}/events")
def thread_events(thread_id: str):
    return {"events": memory.events(thread_id)}


@app.get("/api/threads/{thread_id}/context")
def thread_context(thread_id: str):
    return memory.compact_context(thread_id)


@app.post("/api/threads/{thread_id}/feedback")
def feedback(thread_id: str, request: FeedbackRequest):
    memory.begin_thread(thread_id, request.user_id)
    memory.feedback(thread_id, request.product_id, request.value, request.note)
    return {"accepted": True}


@app.post("/api/threads/{thread_id}/cancel")
def cancel(thread_id: str):
    memory.cancel(thread_id)
    return {"cancelled": True}


@app.websocket("/ws/{thread_id}")
async def events(websocket: WebSocket, thread_id: str):
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        await websocket.close(code=1008, reason="Origin not allowed")
        return
    await websocket.accept(); connections[thread_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections[thread_id].discard(websocket)
