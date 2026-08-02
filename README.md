# Best Gift Search

Best Gift Search is a runnable multi-agent gift discovery MVP inspired by the supplied ecommerce-agent architecture brief. A planning agent fans out to recipient, catalog, and value specialists; results are compared with transparent price/shipping totals, streamed to the browser, and persisted as preference memory.

## What works

- Natural-language gift requests with budget, recipient, occasion, interests, country, and exclusions
- Parallel specialist agents and a visible `think → act → observe → reflect` event stream
- Semantic-style catalog retrieval, reranking, price + shipping totals, and explainable match scores
- SQLite-backed threads, preference memory, feedback, cancellation, and replayable events
- Provider-neutral model/catalog adapters, lifecycle hooks, compact checkpoints, and telemetry
- Rubrics-as-Rewards evaluation for relevance, budget fit, diversity, and explainability
- Prompt-injection screening, Unicode normalization, and resilient provider wrappers
- Cross-thread user preference memory plus asynchronous job status and cancellation APIs
- Optional API-key enforcement, per-client rate limiting, request IDs, security headers, and structured access logs
- SQLite-persisted job state and compact replay context for restart-safe operations
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

### Optional live providers

The default remains deterministic and requires no secrets. To enable the official OpenAI Responses API provider:

```bash
pip install '.[ai]'
export OPENAI_API_KEY='...'
export BEST_GIFT_MODEL_PROVIDER=openai
export BEST_GIFT_OPENAI_MODEL=gpt-5.6-luna
```

The summary route uses the latency-oriented model role with reasoning explicitly set to `none`; provider errors or timeouts fall back to the deterministic summary. To connect an approved commerce service, set `BEST_GIFT_CATALOG_URL` to an HTTPS endpoint returning an array matching the `Product` schema, plus `BEST_GIFT_CATALOG_TOKEN` when required. Remote catalog calls use timeout, retry, circuit-breaker, and strict schema validation.

## API

```bash
curl -X POST http://localhost:8000/api/search \
  -H 'content-type: application/json' \
  -d '{"message":"A thoughtful birthday gift for my sister who loves coffee and travel, under $80","country":"US"}'
```

Connect to `ws://localhost:8000/ws/{thread_id}` before submitting a search with the same `thread_id` to watch live agent events. Use `GET /api/threads/{thread_id}`, `GET /api/threads/{thread_id}/events`, `POST /api/threads/{thread_id}/feedback`, and `POST /api/threads/{thread_id}/cancel` for state, replay, learning signals, and cancellation. `GET /api/metrics` exposes lifecycle telemetry.

For durable/background-style execution, create a task with `POST /api/jobs`, poll `GET /api/jobs/{job_id}`, or cancel it with `DELETE /api/jobs/{job_id}`. The in-process job registry is suitable for a single API process; production multi-worker deployments should replace it with Redis/Celery, Dramatiq, or a managed queue.

`GET /api/threads/{thread_id}/context` returns the latest compact checkpoint and a bounded recent event window. Jobs are persisted in SQLite; any job left queued or running during a process restart is recovered as failed rather than remaining stuck. Set `BEST_GIFT_API_KEY` to protect HTTP `/api/*` routes with `X-API-Key`, and tune `BEST_GIFT_RATE_LIMIT` for the per-client one-minute window. For end-user production authentication, replace the shared-key gate with an identity-aware gateway or OIDC middleware.

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

See [Architecture](docs/ARCHITECTURE.md) for runtime boundaries and [Operations](docs/OPERATIONS.md) for failure behavior, deployment guidance, and the production checklist.

## Production integration boundary

The default providers are deterministic so development and CI need no secrets. A live deployment should implement `CatalogProvider.search()` for approved commerce APIs and `ModelProvider.summarize()` for its chosen model gateway, then inject those providers into `AgentLoop`. Keep API keys server-side and preserve the deterministic evaluator as a regression gate.

## Quality checks

```bash
uv run pytest
cd web && npm run build
python -m best_gift_search.eval_runner evaluations/gift_search.jsonl --minimum 55
```

## Responsible recommendations

Every result includes its scoring reasons and total landed cost. Affiliate links are not generated, sponsored placement is not supported, and feedback is stored as an explicit user signal. Live marketplace integrations should add price freshness timestamps, merchant reliability checks, and regional privacy/consent controls.
