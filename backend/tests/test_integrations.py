import hmac
from hashlib import sha256

import pytest

from app.core.config import Settings
from app.integrations.ai import ImpactAIResult, NullAIProvider, provider_from_settings
from app.integrations.billing import BillingService


def test_ai_result_validation_and_null_provider():
    result = ImpactAIResult.model_validate({"is_impacted": True, "severity": "HIGH", "confidence": 0.9, "reason": "Related rule", "relationship_type": "explicit"})
    assert result.severity == "HIGH"
    assert isinstance(provider_from_settings(Settings(ai_provider="none")), NullAIProvider)


@pytest.mark.asyncio
async def test_null_ai_gracefully_returns_none():
    assert await NullAIProvider().analyze_impact({"x": 1}) is None


def test_billing_webhook_signature_verification():
    body = b'{"event":"subscription.created"}'
    secret = "secret"
    signature = hmac.new(secret.encode(), body, sha256).hexdigest()
    billing = BillingService(secret)
    assert billing.verify_webhook(body, signature)
    assert not billing.verify_webhook(body, "bad")
