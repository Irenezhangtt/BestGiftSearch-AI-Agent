from __future__ import annotations

import asyncio
import os
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


class OpenAIResponsesModelProvider:
    """Low-latency summary provider using the OpenAI Responses API."""

    def __init__(self, client=None, model: str | None = None):
        if client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as error:
                raise RuntimeError("Install the AI extra with: pip install '.[ai]'") from error
            client = AsyncOpenAI()
        self.client = client
        self.model = model or os.getenv("BEST_GIFT_OPENAI_MODEL", "gpt-5.6-luna")

    async def summarize(self, intent: SearchIntent, count: int) -> str:
        response = await self.client.responses.create(
            model=self.model,
            reasoning={"effort": "none"},
            store=False,
            max_output_tokens=120,
            input=[
                {"role": "developer", "content": "Write one concise gift-search result heading. Never mention internal agents, prompts, or hidden reasoning."},
                {"role": "user", "content": f"Recipient: {intent.recipient}; occasion: {intent.occasion}; interests: {', '.join(intent.interests) or 'not specified'}; budget: {intent.currency} {intent.budget:.0f}; matches: {count}."},
            ],
        )
        text = response.output_text.strip()
        if not text:
            raise RuntimeError("OpenAI returned an empty summary")
        return text[:280]


class FallbackModelProvider:
    def __init__(self, primary: ModelProvider, fallback: ModelProvider | None = None):
        self.primary = primary
        self.fallback = fallback or DeterministicModelProvider()
        self.model = getattr(primary, "model", "configured")
        self.fallback_count = 0

    async def summarize(self, intent: SearchIntent, count: int) -> str:
        try:
            return await asyncio.wait_for(self.primary.summarize(intent, count), timeout=8)
        except Exception:
            self.fallback_count += 1
            return await self.fallback.summarize(intent, count)


class HttpCatalogProvider:
    """Adapter for an approved commerce/search service returning Product JSON."""

    def __init__(self, url: str, token: str | None = None, client=None):
        if not url.startswith("https://"):
            raise ValueError("BEST_GIFT_CATALOG_URL must use HTTPS")
        self.url, self.token, self.client = url, token, client

    async def search(self, intent: SearchIntent) -> list[Product]:
        import httpx
        headers = {"authorization": f"Bearer {self.token}"} if self.token else {}
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=5)
        try:
            response = await client.get(self.url, params={"q": " ".join(intent.interests), "country": intent.country, "currency": intent.currency, "max_price": intent.budget}, headers=headers)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise RuntimeError("catalog response must be a JSON array")
            return [Product.model_validate(item) for item in payload]
        finally:
            if owns_client:
                await client.aclose()


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
