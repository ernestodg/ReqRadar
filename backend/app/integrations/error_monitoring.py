from __future__ import annotations

from typing import Any

SENSITIVE_HEADER_NAMES = {"authorization", "cookie", "set-cookie", "x-supabase-auth"}
SENSITIVE_KEY_PARTS = ("token", "secret", "password", "authorization", "cookie", "database_url", "api_key")


def scrub_value(value: Any) -> Any:
    if isinstance(value, dict):
        return sanitize_mapping(value)
    if isinstance(value, list):
        return [scrub_value(item) for item in value]
    return value


def sanitize_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in mapping.items():
        key_lower = str(key).lower()
        if key_lower in SENSITIVE_HEADER_NAMES or any(part in key_lower for part in SENSITIVE_KEY_PARTS):
            clean[key] = "[Filtered]"
        elif key_lower in {"data", "body", "json", "form", "files"}:
            clean[key] = "[Filtered]"
        else:
            clean[key] = scrub_value(value)
    return clean


def before_send(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any] | None:
    return sanitize_mapping(event)
