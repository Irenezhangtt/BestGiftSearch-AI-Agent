from __future__ import annotations

import re
import unicodedata


class UnsafeInput(ValueError):
    pass


INJECTION_PATTERNS = (
    r"ignore (?:all |the )?(?:previous|prior|system) instructions",
    r"reveal (?:the )?(?:system prompt|developer message|api key|secret)",
    r"(?:act|pretend) as (?:the )?(?:system|developer)",
    r"<\s*(?:system|developer|tool)[^>]*>",
)


def sanitize_message(message: str) -> str:
    normalized = unicodedata.normalize("NFKC", message).replace("\x00", " ")
    normalized = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in INJECTION_PATTERNS):
        raise UnsafeInput("Request contains instruction-override or secret-extraction language")
    return normalized
