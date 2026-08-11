from __future__ import annotations

import hashlib
import re

PII_PATTERNS: dict[str, str] = {
    "email": r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    "credit_card": r"(?<!\d)(?:\d[ -]?){15}\d(?!\d)",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"(?<!\d)\d{12}(?!\d)",
    "passport_vn": r"(?i)\b[A-Z]{1,2}\d{7}\b",
    "address_vn": r"(?i)\b(?:địa\s*chỉ|dia\s*chi)\s*[:=-]\s*[^,\n;]{5,120}",
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
