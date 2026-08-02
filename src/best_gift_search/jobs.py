from __future__ import annotations

import asyncio
from uuid import uuid4

from .agents import AgentLoop, SearchCancelled
from .models import AgentEvent, JobStatus, SearchRequest


class JobManager:
    def __init__(self, loop: AgentLoop, sink):
        self.loop = loop
        self.sink = sink
        self.jobs: dict[str, JobStatus] = {}
        self.tasks: dict[str, asyncio.Task] = {}

    def submit(self, request: SearchRequest) -> JobStatus:
        job_id = uuid4().hex
        thread_id = request.thread_id or uuid4().hex
        request = request.model_copy(update={"thread_id": thread_id})
        self.jobs[job_id] = JobStatus(id=job_id, status="queued")
        self.tasks[job_id] = asyncio.create_task(self._run(job_id, request))
        return self.jobs[job_id]

    async def _run(self, job_id: str, request: SearchRequest):
        self.jobs[job_id] = JobStatus(id=job_id, status="running")
        try:
            result = await self.loop.run(request, self.sink)
            self.jobs[job_id] = JobStatus(id=job_id, status="complete", result=result)
        except (SearchCancelled, asyncio.CancelledError):
            self.jobs[job_id] = JobStatus(id=job_id, status="cancelled")
        except Exception as error:
            self.jobs[job_id] = JobStatus(id=job_id, status="failed", error=str(error))

    def get(self, job_id: str) -> JobStatus | None:
        return self.jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        task = self.tasks.get(job_id)
        if not task or task.done(): return False
        task.cancel()
        self.jobs[job_id] = JobStatus(id=job_id, status="cancelled")
        return True
