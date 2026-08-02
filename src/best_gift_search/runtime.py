from __future__ import annotations

import os

from .agents import AgentLoop
from .hooks import AgentHook
from .memory import MemoryStore
from .providers import DemoCatalogProvider, DeterministicModelProvider, FallbackModelProvider, HttpCatalogProvider, OpenAIResponsesModelProvider, ResilientCatalogProvider


def build_agent_loop(memory: MemoryStore, hooks: list[AgentHook] | None = None) -> AgentLoop:
    catalog_url = os.getenv("BEST_GIFT_CATALOG_URL")
    catalog = ResilientCatalogProvider(HttpCatalogProvider(catalog_url, os.getenv("BEST_GIFT_CATALOG_TOKEN"))) if catalog_url else DemoCatalogProvider()
    selection = os.getenv("BEST_GIFT_MODEL_PROVIDER", "auto").lower()
    use_openai = selection == "openai" or (selection == "auto" and bool(os.getenv("OPENAI_API_KEY")))
    model = FallbackModelProvider(OpenAIResponsesModelProvider()) if use_openai else DeterministicModelProvider()
    return AgentLoop(memory, catalog=catalog, model=model, hooks=hooks)


def runtime_info(loop: AgentLoop) -> dict:
    return {
        "model_provider": type(loop.model).__name__,
        "catalog_provider": type(loop.catalog).__name__,
        "model": getattr(loop.model, "model", "deterministic"),
        "model_fallbacks": getattr(loop.model, "fallback_count", 0),
    }
