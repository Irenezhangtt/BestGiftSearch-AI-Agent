from __future__ import annotations

from typing import Protocol

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
