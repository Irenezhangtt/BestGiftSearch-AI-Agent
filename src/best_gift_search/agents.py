from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from .catalog import rank, retrieve
from .evaluation import evaluate
from .hooks import AgentHook
from .guardrails import sanitize_message
from .memory import MemoryStore
from .models import AgentEvent, SearchIntent, SearchRequest, SearchResponse
from .providers import CatalogProvider, DemoCatalogProvider, DeterministicModelProvider, ModelProvider

EventSink = Callable[[AgentEvent], Awaitable[None]]


class SearchCancelled(Exception):
    pass


class AgentLoop:
    def __init__(self, memory: MemoryStore, catalog: CatalogProvider | None = None, model: ModelProvider | None = None, hooks: list[AgentHook] | None = None):
        self.memory = memory
        self.catalog = catalog or DemoCatalogProvider()
        self.model = model or DeterministicModelProvider()
        self.hooks = hooks or []

    async def run(self, request: SearchRequest, sink: EventSink) -> SearchResponse:
        started_at = time.perf_counter()
        thread_id = request.thread_id or uuid4().hex
        events: list[AgentEvent] = []
        self.memory.begin_thread(thread_id, request.user_id)

        async def emit(phase: str, agent: str, message: str):
            if self.memory.is_cancelled(thread_id):
                raise SearchCancelled(thread_id)
            for hook in self.hooks: await hook.before_step(thread_id, agent, phase)
            event = AgentEvent(thread_id=thread_id, phase=phase, agent=agent, message=message)
            events.append(event); self.memory.save_event(event); await sink(event)
            for hook in self.hooks: await hook.after_event(event)

        await emit("think", "planner", "Understanding the recipient, occasion, constraints, and desired feeling.")
        safe_request = request.model_copy(update={"message": sanitize_message(request.message)})
        analyzer = getattr(self.model, "analyze", None)
        analyzed = await analyzer(safe_request) if analyzer else None
        intent = analyzed or parse_intent(safe_request)
        self.memory.checkpoint(thread_id, "intent", intent.model_dump())
        await emit("act", "planner", "Forking recipient, catalog, and value specialists in parallel.")

        async def recipient_agent():
            await emit("observe", "recipient", f"Gift profile: {intent.recipient}; interests: {', '.join(intent.interests) or 'open-ended'}.")
            return self.memory.preferences(thread_id, request.user_id)

        async def catalog_agent():
            candidates = await self.catalog.search(intent)
            products = retrieve(intent, candidates, limit=24)
            source = getattr(self.catalog, "source_label", "configured commerce source")
            await emit("observe", "catalog", f"Retrieved {len(products)} diverse candidates from {source}.")
            return products

        async def value_agent():
            await emit("observe", "value", f"Comparing delivered totals in {intent.currency} for {intent.country} under {intent.budget:.0f}.")

        preferences, products, _ = await asyncio.gather(recipient_agent(), catalog_agent(), value_agent())
        recommendations = rank(products, intent, preferences)
        self.memory.checkpoint(thread_id, "ranked", {"product_ids": [item.product.id for item in recommendations]})
        await emit("reflect", "planner", "Reranked for relevance, landed cost, rating, diversity, and remembered feedback.")
        await emit("complete", "planner", f"Selected {len(recommendations)} explainable gift ideas.")
        evaluation = evaluate(intent, recommendations)
        summary = await self.model.summarize(intent, len(recommendations))
        search_time_ms = round((time.perf_counter() - started_at) * 1000)
        response = SearchResponse(thread_id=thread_id, summary=summary, search_time_ms=search_time_ms, intent=intent, recommendations=recommendations, events=events, evaluation=evaluation)
        self.memory.save_response(response)
        return response


def parse_intent(request: SearchRequest) -> SearchIntent:
    text = request.message.lower()
    budget_match = re.search(r"(?:under|below|budget(?: of)?|less than|预算|以内)\D{0,8}[$£€]?(\d+(?:\.\d+)?)", text) or re.search(r"[$£€]\s*(\d+(?:\.\d+)?)", text)
    exclusion_match = re.findall(r"(?:\b(?:no|not|avoid|without)\b|不要|避免|不喜欢|不想要)\s*([a-z\u4e00-\u9fff-]+)", text)
    exclusions = list(dict.fromkeys(term.strip(" -") for term in exclusion_match if term.strip(" -")))

    recipient_terms = [
        ("son", ["son", "儿子"]), ("daughter", ["daughter", "女儿"]), ("child", ["child", "kid", "孩子", "儿童"]),
        ("wife", ["wife", "妻子", "老婆"]), ("husband", ["husband", "丈夫", "老公"]),
        ("mother", ["mother", "mom", "mum", "妈妈", "母亲"]), ("father", ["father", "dad", "爸爸", "父亲"]),
        ("sister", ["sister", "姐姐", "妹妹"]), ("brother", ["brother", "哥哥", "弟弟"]),
        ("coworker", ["coworker", "colleague", "同事"]), ("friend", ["friend", "朋友"]),
    ]
    recipient = next((label for label, terms in recipient_terms if any(re.search(rf"\b{re.escape(term)}\b", text) if term.isascii() else term in text for term in terms)), "someone special")
    occasions = [("birthday", ["birthday", "生日"]), ("anniversary", ["anniversary", "纪念日"]), ("wedding", ["wedding", "婚礼"]), ("graduation", ["graduation", "毕业"]), ("christmas", ["christmas", "圣诞"]), ("valentine", ["valentine", "情人节"]), ("holiday", ["holiday", "节日"])]
    occasion = next((label for label, terms in occasions if any(term in text for term in terms)), "gift")

    vocabulary = {
        "coffee": ["coffee", "espresso", "咖啡"], "travel": ["travel", "trip", "旅行", "旅游"],
        "writing": ["writing", "journal", "写作", "手账"], "art": ["art", "drawing", "painting", "艺术", "画画"],
        "gardening": ["garden", "gardening", "plants", "园艺", "植物"], "cooking": ["cook", "cooking", "做饭", "烹饪"],
        "technology": ["technology", "tech", "gadget", "科技"], "tea": ["tea", "matcha", "茶", "抹茶"],
        "mindfulness": ["mindfulness", "meditation", "正念", "冥想"], "music": ["music", "vinyl", "音乐"],
        "science": ["science", "stem", "科学"], "outdoors": ["outdoors", "camping", "户外", "露营"],
        "hiking": ["hiking", "徒步"], "astronomy": ["astronomy", "stars", "space", "天文", "星空"],
        "romance": ["romance", "romantic", "浪漫"], "collecting": ["collecting", "collector", "收藏"],
    }
    interests = [label for label, terms in vocabulary.items() if any(term in text for term in terms)]
    preference_match = re.search(r"(?:loves?|likes?|enjoys?|interested in|into)\s+([^,.;]+?)(?:\s+(?:under|below|with a budget|but|and no)\b|[,.;]|$)", text)
    if preference_match:
        candidates = re.split(r"\s+(?:and|or)\s+|\s*&\s*", preference_match.group(1))
        stop = {"gift", "gifts", "something", "things", "who", "that", "the", "a", "an"}
        interests.extend(candidate.strip(" -") for candidate in candidates if 1 <= len(candidate.split()) <= 3 and candidate.strip(" -") not in stop)
    interests = list(dict.fromkeys(interest for interest in interests if interest and not any(excluded in interest or interest in excluded for excluded in exclusions)))
    return SearchIntent(recipient=recipient, occasion=occasion, interests=interests, exclusions=exclusions, budget=float(budget_match.group(1)) if budget_match else 100, country=request.country.upper(), currency=request.currency.upper())
