# Best Gift Search architecture

## Request lifecycle

1. `ProductionMiddleware` authenticates optional service keys, applies a bounded per-client rate limit, assigns a request ID, and records a structured access event.
2. `AgentLoop` normalizes and screens the user request, parses a compact intent, and checkpoints it.
3. Recipient, catalog, and value agents execute concurrently. Events are persisted and broadcast over the thread WebSocket.
4. The catalog provider returns candidates. The local retrieval layer combines lexical overlap, explicit interests, affordability, rating, and exclusion signals.
5. Recommendations are reranked by delivered cost and relevance, checkpointed, evaluated by the deterministic rubric, and persisted.
6. The configured model provider writes a short heading. OpenAI failures fall back to the deterministic provider without discarding recommendations.

## Runtime boundaries

| Boundary | Default | Production adapter |
| --- | --- | --- |
| Model | Deterministic | OpenAI Responses API (`gpt-5.6-luna` by default) |
| Catalog | Seeded catalog | HTTPS JSON commerce/search provider |
| State | SQLite | Replace `MemoryStore` with Postgres for multi-instance writes |
| Task execution | In-process asyncio | Redis-backed worker queue for multi-instance deployments |
| Events | Process-local WebSocket registry | Redis pub/sub or managed realtime broker |
| Evaluation | Deterministic CI rubric | Add human labels and model-graded traces after privacy review |

## Persistence

SQLite stores threads, events, feedback, checkpoints, and jobs. Schema initialization is additive. A process restart marks incomplete jobs failed, making interruption explicit. Compact context returns only the latest checkpoint and a bounded recent-event window.

## Provider contracts

`CatalogProvider.search()` returns validated `Product` objects. `ModelProvider.summarize()` returns a user-facing heading and never controls ranking or monetary calculations. Wrappers provide timeout, retry, circuit breaking, and deterministic fallback behavior.

## Deployment topology

The included Compose topology runs one API process and one Vite development server. For production, build the web bundle as static assets behind a CDN, terminate TLS at the edge, use identity-aware authentication, move state and jobs to shared services, and keep all provider secrets server-side.
