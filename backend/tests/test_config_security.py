import pytest

from app.core.config import Settings


def test_production_rejects_dev_auth_bypass():
    settings = Settings(app_env="production", dev_auth_bypass=True)
    with pytest.raises(RuntimeError):
        settings.validate_runtime()


def test_production_requires_supabase_url_when_dev_bypass_disabled():
    settings = Settings(app_env="production", dev_auth_bypass=False, supabase_url="")
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        settings.validate_runtime()


def test_production_rejects_invalid_supabase_url():
    settings = Settings(app_env="production", dev_auth_bypass=False, supabase_url="http://localhost:54321/auth/v1")
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        settings.validate_runtime()


def test_production_rejects_insecure_frontend_origin():
    settings = Settings(
        app_env="production",
        dev_auth_bypass=False,
        supabase_url="https://thgnjcztzmtjphjmzgtf.supabase.co",
        frontend_origin="http://localhost:5173",
        allowed_hosts="api.example.com",
    )
    with pytest.raises(RuntimeError, match="FRONTEND_ORIGIN"):
        settings.validate_runtime()


def test_production_rejects_wildcard_allowed_hosts():
    settings = Settings(
        app_env="production",
        dev_auth_bypass=False,
        supabase_url="https://thgnjcztzmtjphjmzgtf.supabase.co",
        frontend_origin="https://reqradar.example.com",
        allowed_hosts="*",
    )
    with pytest.raises(RuntimeError, match="ALLOWED_HOSTS"):
        settings.validate_runtime()


def test_production_accepts_valid_supabase_url():
    settings = Settings(
        app_env="production",
        dev_auth_bypass=False,
        supabase_url="https://thgnjcztzmtjphjmzgtf.supabase.co",
        frontend_origin="https://reqradar.example.com",
        allowed_hosts="api.example.com",
    )
    settings.validate_runtime()
