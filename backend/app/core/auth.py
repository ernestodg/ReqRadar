import uuid
from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.db import get_db
from app.models import Workspace
from app.schemas.api import UserContext


DEV_USER_ID = "dev-user"


def get_current_user(authorization: str | None = Header(default=None), x_dev_user_id: str | None = Header(default=None), db: Session = Depends(get_db)) -> UserContext:
    settings = get_settings()
    if settings.dev_auth_bypass:
        user_id = x_dev_user_id or DEV_USER_ID
    else:
        if not authorization:
            raise HTTPException(status_code=401, detail={"message": "Sign in is required."})
        token = authorization.removeprefix("Bearer ").strip()
        if not settings.supabase_jwt_secret:
            raise HTTPException(status_code=500, detail={"message": "Supabase JWT validation is not configured."})
        try:
            claims = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated", options={"verify_aud": False})
        except JWTError:
            raise HTTPException(status_code=401, detail={"message": "Invalid authentication token."}) from None
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
