from __future__ import annotations

import hmac
import json
import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


log = logging.getLogger("best_gift_search.requests")
log.setLevel(logging.INFO)


class ProductionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str | None, rate_limit_per_minute: int):
        super().__init__(app)
        self.api_key = api_key
        self.rate_limit = rate_limit_per_minute
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", uuid4().hex)
        started = time.perf_counter()
        if request.url.path.startswith("/api/"):
            if self.api_key and not hmac.compare_digest(request.headers.get("x-api-key", ""), self.api_key):
                return JSONResponse({"detail": "Invalid or missing API key"}, status_code=401, headers={"x-request-id": request_id})
            client = request.client.host if request.client else "unknown"
            now = time.monotonic(); bucket = self.requests[client]
            while bucket and bucket[0] < now - 60: bucket.popleft()
            if len(bucket) >= self.rate_limit:
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers={"retry-after": "60", "x-request-id": request_id})
            bucket.append(now)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["referrer-policy"] = "no-referrer"
        log.info(json.dumps({"request_id": request_id, "method": request.method, "path": request.url.path, "status": response.status_code, "duration_ms": round((time.perf_counter()-started)*1000, 1)}))
        return response
