from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from uuid import uuid4

from .catalog import rank, retrieve
from .memory import MemoryStore
from .models import AgentEvent, SearchIntent, SearchRequest, SearchResponse

EventSink = Callable[[AgentEvent], Awaitable[None]]


class AgentLoop:
    def __init__(self, memory: MemoryStore):
        self.memory = memory

    async def run(self, request: SearchRequest, sink: EventSink) -> SearchResponse:
        thread_id = request.thread_id or uuid4().hex
        events: list[AgentEvent] = []

        async def emit(phase: str, agent: str, message: str):
            event = AgentEvent(thread_id=thread_id, phase=phase, agent=agent, message=message)
            events.append(event); self.memory.save_event(event); await sink(event)

        await emit("think", "planner", "Understanding the recipient, occasion, constraints, and desired feeling.")
        intent = parse_intent(request)
        await emit("act", "planner", "Forking recipient, catalog, and value specialists in parallel.")

        async def recipient_agent():
            await asyncio.sleep(0)
            await emit("observe", "recipient", f"Gift profile: {intent.recipient}; interests: {', '.join(intent.interests) or 'open-ended'}.")
            return self.memory.preferences(thread_id)

        async def catalog_agent():
            await asyncio.sleep(0)
            products = retrieve(intent)
            await emit("observe", "catalog", f"Retrieved {len(products)} diverse candidates from the global demo catalog.")
            return products

        async def value_agent():
            await asyncio.sleep(0)
            await emit("observe", "value", f"Comparing delivered totals in {intent.currency} for {intent.country} under {intent.budget:.0f}.")

        preferences, products, _ = await asyncio.gather(recipient_agent(), catalog_agent(), value_agent())
        recommendations = rank(products, intent, preferences)
        await emit("reflect", "planner", "Reranked for relevance, landed cost, rating, diversity, and remembered feedback.")
        await emit("complete", "planner", f"Selected {len(recommendations)} explainable gift ideas.")
        response = SearchResponse(thread_id=thread_id, summary=f"Best matches for {intent.recipient} — balanced for meaning, quality, and delivered cost.", intent=intent, recommendations=recommendations, events=events)
        self.memory.save_response(response)
        return response


def parse_intent(request: SearchRequest) -> SearchIntent:
    text = request.message.lower()
    budget_match = re.search(r"(?:under|below|budget(?: of)?|less than)\s*[$£€]?\s*(\d+(?:\.\d+)?)", text)
    recipient_match = re.search(r"(?:for my|for an?|for)\s+([a-z -]{2,35}?)(?:\s+(?:who|that|on|for|under|below)|[,.;]|$)", text)
    occasion = next((x for x in ["birthday", "anniversary", "wedding", "graduation", "holiday", "christmas", "valentine"] if x in text), "gift")
    vocabulary = ["coffee", "travel", "writing", "art", "gardening", "cooking", "technology", "tea", "mindfulness", "music", "science", "family", "outdoors", "hiking", "astronomy", "romance", "collecting"]
    interests = [word for word in vocabulary if word in text]
    exclusion_match = re.findall(r"(?:no|not|avoid|without)\s+([a-z]+)", text)
    return SearchIntent(recipient=(recipient_match.group(1).strip() if recipient_match else "someone special"), occasion=occasion, interests=interests, exclusions=exclusion_match, budget=float(budget_match.group(1)) if budget_match else 100, country=request.country.upper(), currency=request.currency.upper())
