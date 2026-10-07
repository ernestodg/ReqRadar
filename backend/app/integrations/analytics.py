from functools import lru_cache
from typing import Any

from posthog import Posthog

from app.core.config import Settings, get_settings


SENSITIVE_MARKERS = (
    "SECRET REQUIREMENT TEXT",
    "Bearer ",
    "reviewer confidential note",
)


class Analytics:
    def capture(self, distinct_id: str, event: str, properties: dict[str, Any]) -> None:
        return None


class NullAnalytics(Analytics):
    pass


class PostHogAnalytics(Analytics):
    def __init__(self, api_key: str, host: str, timeout: int = 3) -> None:
        self.client = Posthog(project_api_key=api_key, host=host.rstrip("/"), timeout=timeout)

    def capture(self, distinct_id: str, event: str, properties: dict[str, Any]) -> None:
        self.client.capture(distinct_id=distinct_id, event=event, properties=properties)


def safe_properties(settings: Settings, properties: dict[str, Any] | None = None) -> dict[str, Any]:
    clean = {
        "environment": settings.app_env,
        "release": settings.app_release or settings.sentry_release or "",
    }
    for key, value in (properties or {}).items():
        if key in {"message", "reviewer_note", "csv_text", "filename", "authorization", "cookie", "password", "token"}:
            continue
        if isinstance(value, str) and any(marker in value for marker in SENSITIVE_MARKERS):
            continue
        clean[key] = value
    return clean


@lru_cache
def get_analytics() -> Analytics:
    settings = get_settings()
    if not settings.telemetry_enabled or not settings.posthog_api_key:
        return NullAnalytics()
    try:
        return PostHogAnalytics(settings.posthog_api_key, settings.posthog_host)
    except Exception:
        return NullAnalytics()


def capture_event(user_id: str, event: str, properties: dict[str, Any] | None = None) -> None:
    settings = get_settings()
    try:
        get_analytics().capture(user_id, event, safe_properties(settings, properties))
    except Exception:
        return None
