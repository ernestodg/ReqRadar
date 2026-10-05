import hmac
from hashlib import sha256


class BillingService:
    def __init__(self, webhook_secret: str = "") -> None:
        self.webhook_secret = webhook_secret

    def checkout_url(self, plan: str) -> str | None:
        return None

    def verify_webhook(self, body: bytes, signature: str | None) -> bool:
        if not self.webhook_secret:
            return False
        if not signature:
            return False
        digest = hmac.new(self.webhook_secret.encode(), body, sha256).hexdigest()
        return hmac.compare_digest(signature, digest)
