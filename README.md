# Best Gift Search

Best Gift Search is a runnable multi-agent gift discovery MVP inspired by the supplied ecommerce-agent architecture brief. A planning agent fans out to recipient, catalog, and value specialists; results are compared with transparent price/shipping totals, streamed to the browser, and persisted as preference memory.

## What works

- Natural-language gift requests with budget, recipient, occasion, interests, country, and exclusions
- Parallel specialist agents and a visible `think → act → observe → reflect` event stream
- Semantic-style catalog retrieval, reranking, price + shipping totals, and explainable match scores
- SQLite-backed threads, preference memory, feedback, cancellation, and replayable events
- Provider-neutral model/catalog adapters, lifecycle hooks, compact checkpoints, and telemetry
- Rubrics-as-Rewards evaluation for relevance, budget fit, diversity, and explainability
- FastAPI REST/WebSocket API and React + Vite interface
- Deterministic demo mode: no API keys or paid services required

## Run locally

```bash
cp .env.example .env
docker compose up --build
```

Open <http://localhost:5173>. API docs are at <http://localhost:8000/docs>.

Or run without Docker:

```bash
uv sync --extra dev
uv run uvicorn best_gift_search.app:app --reload
cd web && npm install && npm run dev
```

## API

```bash
curl -X POST http://localhost:8000/api/search \
  -H 'content-type: application/json' \
  -d '{"message":"A thoughtful birthday gift for my sister who loves coffee and travel, under $80","country":"US"}'
```

Connect to `ws://localhost:8000/ws/{thread_id}` before submitting a search with the same `thread_id` to watch live agent events. Use `GET /api/threads/{thread_id}`, `GET /api/threads/{thread_id}/events`, `POST /api/threads/{thread_id}/feedback`, and `POST /api/threads/{thread_id}/cancel` for state, replay, learning signals, and cancellation. `GET /api/metrics` exposes lifecycle telemetry.

## Architecture

```text
React/Vite UI ── REST + WebSocket ── FastAPI
                                      │
                                 AgentLoop
                         ┌────────────┼────────────┐
                    Recipient     Catalog       Value
                       Agent        Agent        Agent
                         └────────────┼────────────┘
                               rank + reflect
                                      │
                           SQLite memory/events
```

The catalog and model interfaces in `providers.py` are provider-neutral. Production adapters can connect marketplace/search APIs and a LangChain-compatible model without changing the public API. Retrieval combines lexical overlap, explicit interest matches, affordability, and rating; a vector database can sit behind the catalog provider. Hooks offer a small HarnessMiddleware-style lifecycle surface, while SQLite checkpoints preserve compact state after intent parsing and reranking.

## Production integration boundary

The default providers are deterministic so development and CI need no secrets. A live deployment should implement `CatalogProvider.search()` for approved commerce APIs and `ModelProvider.summarize()` for its chosen model gateway, then inject those providers into `AgentLoop`. Keep API keys server-side and preserve the deterministic evaluator as a regression gate.

## Quality checks

```bash
uv run pytest
cd web && npm run build
```

## Responsible recommendations

Every result includes its scoring reasons and total landed cost. Affiliate links are not generated, sponsored placement is not supported, and feedback is stored as an explicit user signal. Live marketplace integrations should add price freshness timestamps, merchant reliability checks, and regional privacy/consent controls.
