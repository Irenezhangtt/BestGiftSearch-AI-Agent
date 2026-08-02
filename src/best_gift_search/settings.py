from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    cors_origins: tuple[str, ...]
    api_key: str | None
    rate_limit_per_minute: int

    @classmethod
    def from_env(cls) -> "Settings":
        origins = tuple(item.strip() for item in os.getenv("BEST_GIFT_CORS", "http://localhost:5173").split(",") if item.strip())
        return cls(cors_origins=origins, api_key=os.getenv("BEST_GIFT_API_KEY") or None, rate_limit_per_minute=max(1, int(os.getenv("BEST_GIFT_RATE_LIMIT", "120"))))
