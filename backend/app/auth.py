from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from app.db import get_db
from app.utils import serialize_doc

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

bearer_scheme = HTTPBearer(auto_error=False)


def _jwt_secret() -> str:
    # Keep in backend env in future; default only for dev/testing.
    return os.environ.get("JWT_SECRET", "dev_jwt_secret_change_me")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(*, subject: str, organization_id: str, roles: list[str], minutes: int = 60 * 12) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "org": organization_id,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token süresi doldu")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Geçersiz token")


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Giriş gerekli")

    payload = decode_token(credentials.credentials)

    db = await get_db()
    user = await db.users.find_one({"email": payload.get("sub"), "organization_id": payload.get("org")})
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")

    return serialize_doc(user)


def require_roles(required: list[str]):
    async def _dep(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        roles = set(user.get("roles") or [])
        if not roles.intersection(set(required)):
            raise HTTPException(status_code=403, detail="Yetki yok")
        return user

    return _dep
