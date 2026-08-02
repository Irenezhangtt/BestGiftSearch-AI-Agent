# Operations guide

## Health and diagnostics

- `GET /health` reports the active model/catalog provider and fallback count.
- `GET /api/metrics` reports lifecycle event totals and tracked threads.
- Every HTTP response carries `X-Request-ID` plus defensive content/referrer headers.
- Access logs are JSON and include request ID, method, path, status, and duration.

## Failure behavior

- OpenAI timeout or error: recommendation flow succeeds with a deterministic heading.
- Catalog transient error: retry with exponential backoff; repeated errors open the circuit.
- Process restart: queued/running jobs become failed with an interruption reason.
- Unsafe instruction-override input: synchronous search returns HTTP 422.
- Rate limit: HTTP 429 with `Retry-After: 60`.

## Production checklist

- Configure HTTPS and an identity-aware gateway.
- Store `OPENAI_API_KEY` and catalog tokens in a secret manager.
- Set exact CORS origins; never use `*` with credentials.
- Replace the shared API key with OIDC/JWT validation for end users.
- Move SQLite and in-process jobs/events to shared production services before horizontal scaling.
- Add marketplace freshness timestamps, merchant reliability rules, and affiliate disclosures.
- Run `pytest`, the deterministic evaluation suite, and the web production build for every release.
- Monitor fallback counts, latency, 429s, catalog circuit state, quality scores, and user feedback.

## Data handling

The demo stores opaque user IDs, thread content, feedback, events, and recommendation state. Do not place names, addresses, payment data, or provider secrets in `user_id` or search prompts. A production privacy program should define retention, deletion, export, consent, and regional data residency before collecting identifiable information.
