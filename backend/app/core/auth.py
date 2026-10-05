import uuid
from functools import lru_cache
from fastapi import Depends, Header, HTTPException
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWKClient, PyJWKClientError, decode as jwt_decode
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings, validate_supabase_url
from app.core.db import get_db
from app.models import Workspace
from app.schemas.api import UserContext


DEV_USER_ID = "dev-user"
SUPPORTED_JWT_ALGORITHMS = ("RS256", "ES256")
AUTHENTICATED_AUDIENCE = "authenticated"


def supabase_issuer(settings: Settings) -> str:
    return f"{validate_supabase_url(settings.supabase_url)}/auth/v1"


def supabase_jwks_url(settings: Settings) -> str:
    return f"{supabase_issuer(settings)}/.well-known/jwks.json"


@lru_cache(maxsize=8)
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300)


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail={"message": "Sign in is required."})
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail={"message": "Invalid authentication token."})
    return token.strip()


def verify_supabase_access_token(token: str, settings: Settings) -> dict:
    try:
        issuer = supabase_issuer(settings)
        signing_key = get_jwks_client(supabase_jwks_url(settings)).get_signing_key_from_jwt(token)
        return jwt_decode(
            token,
            signing_key.key,
            algorithms=list(SUPPORTED_JWT_ALGORITHMS),
            audience=AUTHENTICATED_AUDIENCE,
            issuer=issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except RuntimeError:
        raise HTTPException(status_code=500, detail={"message": "Supabase JWT validation is not configured."}) from None
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"message": "Invalid authentication token."}) from None
    except (InvalidTokenError, PyJWKClientError):
        raise HTTPException(status_code=401, detail={"message": "Invalid authentication token."}) from None


def get_current_user(authorization: str | None = Header(default=None), x_dev_user_id: str | None = Header(default=None), db: Session = Depends(get_db)) -> UserContext:
    settings = get_settings()
    if settings.dev_auth_bypass:
        user_id = x_dev_user_id or DEV_USER_ID
    else:
        claims = verify_supabase_access_token(extract_bearer_token(authorization), settings)
        user_id = claims.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail={"message": "Authentication token is missing a subject."})
    workspace = db.scalar(select(Workspace).where(Workspace.owner_user_id == user_id))
    if workspace is None:
        workspace = Workspace(id=uuid.uuid4(), name="My Workspace", owner_user_id=user_id, plan="FREE")
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
    return UserContext(user_id=user_id, workspace_id=workspace.id, workspace_name=workspace.name)
