from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jwt import PyJWKClientError, encode as jwt_encode, get_unverified_header

from app.core import auth
from app.core.config import Settings


SUPABASE_URL = "https://thgnjcztzmtjphjmzgtf.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
AUDIENCE = "authenticated"


@pytest.fixture()
def signing_keys():
    return {
        "primary": rsa.generate_private_key(public_exponent=65537, key_size=2048),
        "other": rsa.generate_private_key(public_exponent=65537, key_size=2048),
    }


class StaticJwksClient:
    def __init__(self, keys_by_kid):
        self.keys_by_kid = keys_by_kid

    def get_signing_key_from_jwt(self, token: str):
        kid = get_unverified_header(token).get("kid")
        key = self.keys_by_kid.get(kid)
        if key is None:
            raise PyJWKClientError("No matching key")
        return SimpleNamespace(key=key)


def production_settings() -> Settings:
    return Settings(app_env="production", dev_auth_bypass=False, supabase_url=SUPABASE_URL)


def token(private_key, *, kid: str = "primary", issuer: str = ISSUER, audience: str = AUDIENCE, subject: str | None = "user-1", expires_delta: timedelta = timedelta(minutes=5), algorithm: str = "RS256") -> str:
    now = datetime.now(UTC)
    claims = {
        "iss": issuer,
        "aud": audience,
        "exp": now + expires_delta,
    }
    if subject is not None:
        claims["sub"] = subject
    return jwt_encode(claims, private_key, algorithm=algorithm, headers={"kid": kid})


def configure_production_auth(monkeypatch, signing_keys):
    monkeypatch.setattr(auth, "get_settings", production_settings)
    monkeypatch.setattr(auth, "get_jwks_client", lambda _: StaticJwksClient({"primary": signing_keys["primary"].public_key()}))


def assert_auth_rejected(client, bearer_token: str):
    response = client.get("/me", headers={"Authorization": f"Bearer {bearer_token}"})
    assert response.status_code == 401


def test_valid_asymmetric_token_returns_user_context(client, monkeypatch, signing_keys):
    configure_production_auth(monkeypatch, signing_keys)
    response = client.get("/me", headers={"Authorization": f"Bearer {token(signing_keys['primary'])}"})

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user-1"
    assert body["workspace_name"] == "My Workspace"


def test_valid_es256_token_returns_user_context(client, monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(auth, "get_settings", production_settings)
    monkeypatch.setattr(auth, "get_jwks_client", lambda _: StaticJwksClient({"ec": private_key.public_key()}))

    response = client.get("/me", headers={"Authorization": f"Bearer {token(private_key, kid='ec', algorithm='ES256')}"})

    assert response.status_code == 200
    assert response.json()["user_id"] == "user-1"


def test_expired_token_is_rejected(client, monkeypatch, signing_keys):
    configure_production_auth(monkeypatch, signing_keys)
    assert_auth_rejected(client, token(signing_keys["primary"], expires_delta=timedelta(minutes=-1)))


def test_wrong_issuer_is_rejected(client, monkeypatch, signing_keys):
    configure_production_auth(monkeypatch, signing_keys)
    assert_auth_rejected(client, token(signing_keys["primary"], issuer="https://other.supabase.co/auth/v1"))


def test_wrong_audience_is_rejected(client, monkeypatch, signing_keys):
    configure_production_auth(monkeypatch, signing_keys)
    assert_auth_rejected(client, token(signing_keys["primary"], audience="anon"))


def test_wrong_signing_key_is_rejected(client, monkeypatch, signing_keys):
    configure_production_auth(monkeypatch, signing_keys)
    assert_auth_rejected(client, token(signing_keys["other"]))


def test_malformed_token_is_rejected(client, monkeypatch, signing_keys):
    configure_production_auth(monkeypatch, signing_keys)
    assert_auth_rejected(client, "not.a.jwt")


def test_missing_subject_is_rejected(client, monkeypatch, signing_keys):
    configure_production_auth(monkeypatch, signing_keys)
    assert_auth_rejected(client, token(signing_keys["primary"], subject=None))


def test_missing_authorization_header_is_rejected(client, monkeypatch, signing_keys):
    configure_production_auth(monkeypatch, signing_keys)
    response = client.get("/me")
    assert response.status_code == 401


def test_hs256_token_is_not_accepted(client, monkeypatch, signing_keys):
    configure_production_auth(monkeypatch, signing_keys)
    hs_token = token("legacy-secret", algorithm="HS256")
    assert_auth_rejected(client, hs_token)


def test_local_dev_auth_bypass_is_preserved(client, monkeypatch):
    monkeypatch.setattr(auth, "get_settings", lambda: Settings(dev_auth_bypass=True))
    response = client.get("/me", headers={"x-dev-user-id": "local-user"})

    assert response.status_code == 200
    assert response.json()["user_id"] == "local-user"
