from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Protocol, TypeVar

from .catalog import PRODUCTS
from .models import Product, SearchIntent


class CatalogProvider(Protocol):
    """Provider seam for marketplace, search API, or vector-store adapters."""

    async def search(self, intent: SearchIntent) -> list[Product]: ...


class DemoCatalogProvider:
    async def search(self, intent: SearchIntent) -> list[Product]:
        return list(PRODUCTS)


class ModelProvider(Protocol):
    """Small model surface that can be implemented by OpenAI/LangChain later."""

    async def summarize(self, intent: SearchIntent, count: int) -> str: ...


class DeterministicModelProvider:
    async def summarize(self, intent: SearchIntent, count: int) -> str:
        return f"{count} thoughtful matches for {intent.recipient}, balanced for meaning, quality, and delivered cost."


T = TypeVar("T")


@dataclass
class ProviderPolicy:
    timeout_seconds: float = 5
    retries: int = 2
    failure_threshold: int = 3
    reset_seconds: float = 30


class ResilientCatalogProvider:
    """Timeout, retry, and circuit-breaker wrapper for live commerce providers."""

    def __init__(self, inner: CatalogProvider, policy: ProviderPolicy | None = None):
        self.inner = inner
        self.policy = policy or ProviderPolicy()
        self.failures = 0
        self.opened_at = 0.0

    async def search(self, intent: SearchIntent) -> list[Product]:
        if self.failures >= self.policy.failure_threshold and time.monotonic() - self.opened_at < self.policy.reset_seconds:
            raise RuntimeError("catalog provider circuit is open")
        last_error: Exception | None = None
        for attempt in range(self.policy.retries + 1):
            try:
                result = await asyncio.wait_for(self.inner.search(intent), self.policy.timeout_seconds)
                self.failures = 0
                return result
            except (TimeoutError, OSError, RuntimeError) as error:
                last_error = error
                if attempt < self.policy.retries:
                    await asyncio.sleep(0.05 * 2**attempt)
        self.failures += 1
        self.opened_at = time.monotonic()
        raise RuntimeError("catalog provider unavailable") from last_error
