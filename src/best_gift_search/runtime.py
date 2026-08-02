from __future__ import annotations

import os

from .agents import AgentLoop
from .hooks import AgentHook
from .memory import MemoryStore
from .providers import AnthropicModelProvider, DemoCatalogProvider, DeterministicModelProvider, FallbackCatalogProvider, FallbackModelProvider, HttpCatalogProvider, OpenAIResponsesModelProvider, ResilientCatalogProvider, SerpApiCatalogProvider


def build_agent_loop(memory: MemoryStore, hooks: list[AgentHook] | None = None) -> AgentLoop:
    catalog_url = os.getenv("BEST_GIFT_CATALOG_URL")
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if serpapi_key:
        catalog = FallbackCatalogProvider(ResilientCatalogProvider(SerpApiCatalogProvider(serpapi_key)))
    elif catalog_url:
        catalog = FallbackCatalogProvider(ResilientCatalogProvider(HttpCatalogProvider(catalog_url, os.getenv("BEST_GIFT_CATALOG_TOKEN"))))
    else:
        catalog = DemoCatalogProvider()
    selection = os.getenv("BEST_GIFT_MODEL_PROVIDER", "auto").lower()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    use_anthropic = bool(anthropic_key) and selection in {"auto", "anthropic", "claude"}
    use_openai = selection == "openai" or (selection == "auto" and not use_anthropic and bool(os.getenv("OPENAI_API_KEY")))
    if use_anthropic: model = FallbackModelProvider(AnthropicModelProvider(anthropic_key))
    elif use_openai: model = FallbackModelProvider(OpenAIResponsesModelProvider())
    else: model = DeterministicModelProvider()
    return AgentLoop(memory, catalog=catalog, model=model, hooks=hooks)


def runtime_info(loop: AgentLoop) -> dict:
    return {
        "model_provider": type(loop.model).__name__,
        "catalog_provider": type(loop.catalog).__name__,
        "catalog_source": getattr(loop.catalog, "source_label", "configured catalog"),
        "catalog_fallbacks": getattr(loop.catalog, "fallback_count", 0),
        "model": getattr(loop.model, "model", "deterministic"),
        "model_fallbacks": getattr(loop.model, "fallback_count", 0),
    }
