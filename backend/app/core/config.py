from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://radar:radar@postgres:5432/radar"
    frontend_origin: str = "http://localhost:5173"
    dev_auth_bypass: bool = True
    ai_provider: str = "none"
    ai_model: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""
    posthog_api_key: str = ""
    posthog_host: str = "https://app.posthog.com"
    billing_enabled: bool = False
    paddle_webhook_secret: str = ""
    sentry_dsn: str = ""
    high_threshold: int = 70
    medium_threshold: int = 40
    upload_limit_bytes: int = Field(default=10 * 1024 * 1024)

    def validate_runtime(self) -> None:
        if self.app_env == "production" and self.dev_auth_bypass:
            raise RuntimeError("DEV_AUTH_BYPASS cannot be enabled in production.")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
