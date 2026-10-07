from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://radar:radar@postgres:5432/radar"
    frontend_origin: str = "http://localhost:5173"
    allowed_hosts: str = "*"
    dev_auth_bypass: bool = True
    ai_provider: str = "none"
    ai_model: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    app_release: str = ""
    telemetry_enabled: bool = False
    posthog_api_key: str = ""
    posthog_host: str = "https://app.posthog.com"
    billing_enabled: bool = False
    paddle_webhook_secret: str = ""
    sentry_dsn: str = ""
    sentry_environment: str = ""
    sentry_release: str = ""
    high_threshold: int = 70
    medium_threshold: int = 40
    upload_limit_bytes: int = Field(default=10 * 1024 * 1024)

    def validate_runtime(self) -> None:
        if self.app_env == "production" and self.dev_auth_bypass:
            raise RuntimeError("DEV_AUTH_BYPASS cannot be enabled in production.")
        if self.app_env == "production":
            validate_supabase_url(self.supabase_url)
            validate_https_origin(self.frontend_origin, "FRONTEND_ORIGIN")
            if self.allowed_hosts.strip() == "*":
                raise RuntimeError("ALLOWED_HOSTS must be explicitly configured in production.")


def validate_supabase_url(value: str) -> str:
    parsed = urlparse(value.rstrip("/"))
    if parsed.scheme != "https" or not parsed.netloc or parsed.path:
        raise RuntimeError("SUPABASE_URL must be a valid HTTPS project URL.")
    return value.rstrip("/")


def validate_https_origin(value: str, name: str) -> str:
    parsed = urlparse(value.rstrip("/"))
    if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.params or parsed.query or parsed.fragment:
        raise RuntimeError(f"{name} must be a valid HTTPS origin.")
    return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
