from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
from dataclasses import dataclass
from typing import Protocol, TypeVar

from .catalog import PRODUCTS
from .models import Product, SearchIntent


class CatalogProvider(Protocol):
    """Provider seam for marketplace, search API, or vector-store adapters."""

    async def search(self, intent: SearchIntent) -> list[Product]: ...


class DemoCatalogProvider:
    source_label = "offline fallback catalog"

    async def search(self, intent: SearchIntent) -> list[Product]:
        return list(PRODUCTS)


def build_product_query(intent: SearchIntent) -> str:
    """Turn structured gift intent into a marketplace-friendly search query."""
    parts = [intent.occasion if intent.occasion != "gift" else "", "gift", f"for {intent.recipient}", *intent.interests]
    if intent.exclusions:
        parts.extend(f"-{term}" for term in intent.exclusions)
    return " ".join(part for part in parts if part).strip()


class SerpApiCatalogProvider:
    """Live Google Shopping adapter returning real products from across the web."""

    source_label = "live Google Shopping results"
    endpoint = "https://serpapi.com/search.json"

    def __init__(self, api_key: str, client=None):
        if not api_key:
            raise ValueError("SERPAPI_API_KEY is required")
        self.api_key, self.client = api_key, client

    async def search(self, intent: SearchIntent) -> list[Product]:
        import httpx
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=8)
        try:
            response = await client.get(self.endpoint, params={
                "engine": "google_shopping",
                "q": build_product_query(intent),
                "gl": intent.country.lower(),
                "hl": "en",
                "min_price": round(intent.budget * 0.5, 2),
                "max_price": round(intent.budget, 2),
                "api_key": self.api_key,
            })
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(str(payload["error"]))
            raw_products = payload.get("shopping_results") or payload.get("inline_shopping_results") or []
            products = [product for item in raw_products if (product := self._convert(item, intent))]
            if not products:
                raise RuntimeError("live shopping search returned no valid products")
            return products[:40]
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _convert(item: dict, intent: SearchIntent) -> Product | None:
        title = str(item.get("title") or "").strip()
        url = str(item.get("link") or item.get("product_link") or "").strip()
        image = str(item.get("thumbnail") or item.get("serpapi_thumbnail") or "").strip()
        extracted = item.get("extracted_price")
        if extracted is None:
            match = re.search(r"\d[\d,]*(?:\.\d+)?", str(item.get("price") or ""))
            extracted = match.group(0).replace(",", "") if match else None
        try:
            price = float(extracted)
        except (TypeError, ValueError):
            return None
        if not title or not url.startswith("https://") or not image.startswith("https://"):
            return None
        merchant = str(item.get("source") or item.get("seller") or "Google Shopping merchant")[:120]
        extensions = item.get("extensions") if isinstance(item.get("extensions"), list) else []
        description = " · ".join(str(value) for value in extensions[:3]) or f"Available from {merchant}; price and availability may change."
        product_id = str(item.get("product_id") or hashlib.sha256(f"{title}|{url}".encode()).hexdigest()[:20])
        title_terms = title.lower()
        matched_interests = [interest for interest in intent.interests if interest.lower() in title_terms]
        category_rules = [
            ("educational kits", ["kit", "experiment", "stem", "robot", "telescope", "microscope", "puzzle", "game"]),
            ("books", ["book", "journal", "guide", "encyclopedia"]),
            ("art and decor", ["print", "poster", "art", "painting", "frame", "map"]),
            ("electronics", ["electronic", "speaker", "headphone", "camera", "digital", "smart"]),
            ("toys", ["toy", "lego", "plush", "figure", "model"]),
            ("apparel", ["shirt", "hoodie", "sweater", "sock", "hat", "jacket"]),
            ("jewelry", ["necklace", "bracelet", "ring", "earring", "jewelry"]),
            ("food and drink", ["coffee", "tea", "chocolate", "snack", "food", "candy"]),
            ("homeware", ["mug", "cup", "blanket", "lamp", "pillow", "bottle"]),
            ("outdoors", ["camp", "hiking", "outdoor", "picnic", "garden"]),
            ("stationery", ["pen", "notebook", "stationery", "card"]),
        ]
        category = next((label for label, terms in category_rules if any(term in title_terms for term in terms)), "other gifts")
        return Product(
            id=f"live-{product_id}", name=title[:180], description=description[:500],
            category=category, interests=matched_interests, price=price,
            shipping={intent.country: 0}, url=url, image=image, merchant=merchant,
            rating=max(0, min(5, float(item.get("rating") or 4.0))),
        )


class FallbackCatalogProvider:
    """Use the local catalog only when the configured live source is unavailable."""

    def __init__(self, primary: CatalogProvider, fallback: CatalogProvider | None = None):
        self.primary, self.fallback = primary, fallback or DemoCatalogProvider()
        self.fallback_count = 0

    @property
    def source_label(self) -> str:
        return getattr(self.primary, "source_label", "live commerce search")

    async def search(self, intent: SearchIntent) -> list[Product]:
        try:
            return await self.primary.search(intent)
        except Exception:
            self.fallback_count += 1
            return await self.fallback.search(intent)


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
