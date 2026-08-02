from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

from .models import AgentEvent


class AgentHook(Protocol):
    async def before_step(self, thread_id: str, agent: str, phase: str): ...
    async def after_event(self, event: AgentEvent): ...


@dataclass
class MetricsHook:
    """Lightweight HarnessMiddleware-style telemetry without vendor lock-in."""

    started: dict[str, float] = field(default_factory=dict)
    event_counts: dict[str, int] = field(default_factory=dict)

    async def before_step(self, thread_id: str, agent: str, phase: str):
        self.started.setdefault(thread_id, time.perf_counter())

    async def after_event(self, event: AgentEvent):
        self.event_counts[event.phase] = self.event_counts.get(event.phase, 0) + 1

    def snapshot(self) -> dict:
        return {"event_counts": self.event_counts, "tracked_threads": len(self.started)}
