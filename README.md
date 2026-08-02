# Best Gift Search

[Public demo](https://irenezhangtt.github.io/BestGiftSearch-AI-Agent/) · [API docs after local start](http://localhost:8000/docs) · [Architecture](docs/ARCHITECTURE.md) · [Operations](docs/OPERATIONS.md)

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
- Optional live Google Shopping retrieval: prompt-derived queries return current products, images, prices, merchants, and outbound links

## Choose how to view it

| Goal | Best path | What you get |
| --- | --- | --- |
| See the visual result now | Open the hosted showcase (link below after deployment) | Responsive product cards, quality rubric, and agent-flow explanation |
| Run the complete product | Docker Compose | React UI + FastAPI + WebSocket + SQLite |
| Develop either layer | Native Python/Node setup | Hot reload and direct access to both services |

Open the public **[GitHub Pages interactive demo](https://irenezhangtt.github.io/BestGiftSearch-AI-Agent/)**. Its browser-side deterministic recommender semantically combines recipient type, age, occasion, interests, exclusions, and English or Chinese budget terms. Budget is treated as a hard constraint whenever an eligible item exists, and the shortlist is diversified across product categories. Sixteen representative products span multiple price tiers so changing the prompt materially changes the recommendations. A second [Sites showcase](https://best-gift-search-ai.tina219127.chatgpt.site) is also available. Local/Docker builds of the same UI talk to the real FastAPI service in `src/best_gift_search/`.

## Quick start with Docker (recommended)

Prerequisites: Docker Desktop with Compose v2 and ports `5173` and `8000` available.

```bash
git clone https://github.com/Irenezhangtt/BestGiftSearch-AI-Agent.git
cd BestGiftSearch-AI-Agent
cp .env.example .env
docker compose up --build
```

Then open:

- Web app: <http://localhost:5173>
- Interactive API docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Stop the stack with `Ctrl+C`, or run `docker compose down` from another terminal. SQLite data remains in the configured Docker volume.

## Local development without Docker

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), and Node.js 22+.

Terminal 1 — backend:

```bash
git clone https://github.com/Irenezhangtt/BestGiftSearch-AI-Agent.git
cd BestGiftSearch-AI-Agent
cp .env.example .env
uv sync --extra dev
uv run uvicorn best_gift_search.app:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 — frontend:

```bash
cd BestGiftSearch-AI-Agent/web
npm install
npm run dev
```

Open <http://localhost:5173>. The default configuration uses an in-repository deterministic catalog and summary provider, so the whole flow works without paid services or API keys.

### Try the interface

1. Describe a recipient, occasion, interests, destination country, and approximate budget.
2. Select `US`, `CA`, or `GB`, then choose **Find gifts**.
3. Watch the specialist-agent events appear while the search runs.
4. Review landed costs, match reasons, caveats, and the automated quality rubric.
5. Use **Yes/No** feedback; the signal is stored in SQLite and can influence later searches for the same browser user.

Example prompt:

```text
A thoughtful birthday gift for my sister who loves coffee and travel, under $80
```

Additional semantic examples:

```text
A science gift for my 10-year-old son, under $35
An anniversary gift for my wife who loves astronomy, under $60
A thank-you gift for my coworker, no coffee, under $40
给喜欢园艺和做饭的妈妈选生日礼物，预算30美元以内
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

### Dynamic product search from the web

The 16 browser-demo products are an offline fallback, not the production search boundary. When `SERPAPI_API_KEY` is present on the API server, each request follows this live path:

```text
prompt → structured recipient/occasion/interests/exclusions/budget
       → dynamic Google Shopping query
       → up to 40 current web products
       → relevance, delivered-cost, rating, and diversity ranking
       → four explained recommendations in the website
```

The live adapter maps the shopping response into the normal `Product` model, including the current title, price, thumbnail, merchant, rating, and HTTPS shopping link. It supports country targeting and negative search terms. If the shopping service is unavailable, the API records a fallback and uses the local catalog instead of failing the whole request.

Live shopping retrieves a broad candidate set, then prioritizes a price band from 50% to 100% of the stated budget. The server enforces the maximum after shipping, so an over-budget item can never enter the final shortlist. Ranking favors products closer to the budget and selects distinct inferred categories before filling any remaining positions; for example, an `under $80` request prioritizes products from `$40–$80` across different gift types. Applying the band locally preserves useful lower-priced fallbacks when a marketplace has too few candidates in the preferred range.

Never put `SERPAPI_API_KEY` in `VITE_*`, frontend code, or a GitHub Pages variable. Vite values are public browser code. Store the key only in the backend hosting service.

#### Connect the GitHub Pages site to live search

1. Create a [SerpApi](https://serpapi.com/) account and copy its private API key.
2. Deploy this repository's `render.yaml` as a Render Blueprint.
3. In Render, set `SERPAPI_API_KEY` to the private key. The blueprint already sets the GitHub Pages CORS origin and `/health` check.
4. Confirm `https://YOUR-BACKEND.example/health` reports `catalog_source` as `live Google Shopping results`.
5. In GitHub, open **Settings → Secrets and variables → Actions → Variables** and create `BEST_GIFT_API_URL` with the backend origin, without a trailing slash.
6. Run the **deploy-github-pages** workflow again. It automatically disables offline demo mode when `BEST_GIFT_API_URL` exists.

The browser then sends the prompt to the hosted FastAPI agents. The API key remains private on the server, while real product cards and outbound merchant links appear on GitHub Pages.

### Configuration reference

Copy `.env.example` to `.env`; these are the main operational settings:

| Variable | Default/role |
| --- | --- |
| `BEST_GIFT_MODEL_PROVIDER` | `deterministic`; set to `openai` for live summaries |
| `OPENAI_API_KEY` | Required only when the OpenAI provider is enabled |
| `BEST_GIFT_OPENAI_MODEL` | Model used by the optional summary provider |
| `SERPAPI_API_KEY` | Enables dynamic Google Shopping product retrieval on the backend |
| `BEST_GIFT_API_URL` | GitHub Actions variable used by Pages to call the hosted backend |
| `BEST_GIFT_CATALOG_URL` | Optional HTTPS product-catalog endpoint |
| `BEST_GIFT_CATALOG_TOKEN` | Optional server-side bearer token for that endpoint |
| `BEST_GIFT_API_KEY` | Optional shared API key; clients then send `X-API-Key` |
| `BEST_GIFT_RATE_LIMIT` | Per-client HTTP request limit for a one-minute window |
| `BEST_GIFT_DB` | SQLite file location |

Do not expose provider tokens through Vite variables or commit them to Git. Production identity should be enforced at an OIDC-aware gateway; the shared API key is intended as a lightweight deployment control.

## API

```bash
curl -X POST http://localhost:8000/api/search \
  -H 'content-type: application/json' \
  -d '{"message":"A thoughtful birthday gift for my sister who loves coffee and travel, under $80","country":"US"}'
```

The response includes the normalized intent, ranked recommendations, total landed cost, scoring reasons, an evaluation rubric, and the complete orchestration trace. A minimal response inspection looks like:

```bash
curl -s -X POST http://localhost:8000/api/search \
  -H 'content-type: application/json' \
  -d '{"message":"Gift for a coffee-loving traveler under $80","country":"US"}' \
  | python -m json.tool
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
uv run python -m best_gift_search.eval_runner evaluations/gift_search.jsonl --minimum 55
cd web && npm install && npm run build
cd ../site && npm ci && npm test
```

Expected baseline: all backend tests pass, all four deterministic evaluation cases pass the minimum score, and both web builds finish without TypeScript errors. GitHub Actions repeats the backend test, evaluator, and main frontend build on every push and pull request.

## Repository map

```text
src/best_gift_search/   FastAPI routes, agent runtime, providers, guardrails, memory
web/                    Live React/Vite client for the FastAPI service
site/                   Deployable visual showcase (example data, no secrets)
tests/                  API, job, guardrail, provider, and persistence tests
evaluations/            Deterministic Rubrics-as-Rewards scenarios
docs/ARCHITECTURE.md    Runtime design, data flow, and extension boundaries
docs/OPERATIONS.md      Failure modes, observability, security, deployment checklist
```

## Troubleshooting

- **Port already in use:** stop the process using `5173`/`8000`, or change the mapped Docker port and `VITE_API_URL` together.
- **Frontend says “Live connection failed”:** confirm <http://localhost:8000/health> responds and that proxies allow WebSocket upgrades on `/ws/*`.
- **401 from API:** either unset `BEST_GIFT_API_KEY` for local development or send the matching `X-API-Key` header.
- **OpenAI/provider failure:** check the key and model settings. The app intentionally falls back to deterministic summaries after provider timeout/error.
- **Stale local data:** stop the API and remove only the configured development SQLite file, then restart. Do not do this for production data.
- **Remote products rejected:** ensure the catalog URL uses HTTPS and its JSON response matches the `Product` schema.

## Responsible recommendations

Every result includes its scoring reasons and total landed cost. Affiliate links are not generated, sponsored placement is not supported, and feedback is stored as an explicit user signal. The static public demo uses unaffiliated Etsy search links because search result pages are less brittle than individual inventory listings; Etsy is not the intended exclusive production provider. Live marketplace integrations should aggregate multiple approved retailers and add price freshness timestamps, merchant reliability checks, and regional privacy/consent controls.
