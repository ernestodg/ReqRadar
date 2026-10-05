import httpx


class Analytics:
    def track(self, event: str, properties: dict) -> None:
        return None


class PostHogAnalytics(Analytics):
    def __init__(self, api_key: str, host: str = "https://app.posthog.com") -> None:
        self.api_key = api_key
        self.host = host.rstrip("/")

    def track(self, event: str, properties: dict) -> None:
        if not self.api_key:
            return None
        try:
            httpx.post(f"{self.host}/capture/", json={"api_key": self.api_key, "event": event, "properties": properties}, timeout=3)
        except httpx.HTTPError:
            return None
