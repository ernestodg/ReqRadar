import pytest

from app.core.config import Settings


def test_production_rejects_dev_auth_bypass():
    settings = Settings(app_env="production", dev_auth_bypass=True)
    with pytest.raises(RuntimeError):
        settings.validate_runtime()
