from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    message: str = Field(min_length=3, max_length=1200)
    thread_id: str | None = None
    country: str = Field(default="US", min_length=2, max_length=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class SearchIntent(BaseModel):
    recipient: str = "someone special"
    occasion: str = "gift"
    interests: list[str] = []
    exclusions: list[str] = []
    budget: float = 100
    country: str = "US"
    currency: str = "USD"


class Product(BaseModel):
    id: str
    name: str
    description: str
    category: str
    interests: list[str]
    price: float
    shipping: dict[str, float]
    url: str
    image: str
    merchant: str
    rating: float


class Recommendation(BaseModel):
    product: Product
    shipping_cost: float
    total_cost: float
    score: float
    reasons: list[str]
    caveat: str | None = None


class AgentEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    thread_id: str
    phase: Literal["think", "act", "observe", "reflect", "complete", "error"]
    agent: str
    message: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SearchResponse(BaseModel):
    thread_id: str
    summary: str
    intent: SearchIntent
    recommendations: list[Recommendation]
    events: list[AgentEvent]


class FeedbackRequest(BaseModel):
    product_id: str
    value: Literal[-1, 1]
    note: str | None = Field(default=None, max_length=500)
