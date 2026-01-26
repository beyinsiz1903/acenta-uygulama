from __future__ import annotations

from hashlib import sha256
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import hash_password
from app.db import get_db
from app.errors import AppError
from app.services.audit import audit_snapshot, write_audit_log
from app.utils import now_utc

router = APIRouter(prefix="/api/auth/password-reset", tags=["auth_password_reset"])


class PasswordResetValidateResponse(BaseModel):
    status: str = "ok"
    user_email: str
    expires_at: str
    organization_id: str


class PasswordResetConfirmIn(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


def _fingerprint_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()[:12]


async def _load_token_and_user(db, token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not token:
        raise AppError(400, "invalid_token", "Reset bağlantısı geçersiz.")

    token_doc = await db.password_reset_tokens.find_one({"_id": token})
    if not token_doc:
        raise AppError(404, "token_not_found", "Reset bağlantısı bulunamadı.")

    org_id = token_doc.get("organization_id")
    user_id = token_doc.get("user_id")
    if not org_id or not user_id:
        raise AppError(404, "token_not_found", "Reset bağlantısı bulunamadı.")

    user = await db.users.find_one({"_id": user_id, "organization_id": org_id})
    if not user:
        # Mask user existence
        raise AppError(404, "token_not_found", "Reset bağlantısı bulunamadı.")

    return token_doc, user


@router.get("/validate", response_model=PasswordResetValidateResponse)
async def validate_password_reset_token(token: str):
    db = await get_db()

    token_doc, user = await _load_token_and_user(db, token)

    now = now_utc()

    if token_doc.get("used_at") is not None:
        raise AppError(409, "token_used", "Reset bağlantısı daha önce kullanılmış.")

    expires_at = token_doc.get("expires_at")
    if expires_at and expires_at < now:
        raise AppError(409, "token_expired", "Reset bağlantısının süresi dolmuş.")

    org_id = str(token_doc.get("organization_id"))

    return PasswordResetValidateResponse(
        user_email=user.get("email"),
        expires_at=expires_at.isoformat() if expires_at else "",
        organization_id=org_id,
    )


@router.post("/confirm")
async def confirm_password_reset(payload: PasswordResetConfirmIn, request: Request):
    db = await get_db()

    token = payload.token
    new_password = payload.new_password

    if not new_password or len(new_password.strip()) < 8:
        raise AppError(400, "weak_password", "Şifre en az 8 karakter olmalıdır.")

    now = now_utc()

    # Optimistic consume of token: only if not used and not expired
    token_doc = await db.password_reset_tokens.find_one({"_id": token})
    if not token_doc:
        raise AppError(404, "token_not_found", "Reset bağlantısı bulunamadı.")

    org_id = token_doc.get("organization_id")
    user_id = token_doc.get("user_id")
    if not org_id or not user_id:
        raise AppError(404, "token_not_found", "Reset bağlantısı bulunamadı.")

    if token_doc.get("used_at") is not None:
        raise AppError(409, "token_used", "Reset bağlantısı daha önce kullanılmış.")

    expires_at = token_doc.get("expires_at")
    if expires_at and expires_at < now:
        raise AppError(409, "token_expired", "Reset bağlantısının süresi dolmuş.")

    # Reload user with org guard
    user = await db.users.find_one({"_id": user_id, "organization_id": org_id})
    if not user:
        raise AppError(404, "token_not_found", "Reset bağlantısı bulunamadı.")

    # Mark token as used
    await db.password_reset_tokens.update_one(
        {"_id": token, "used_at": None},
        {"$set": {"used_at": now}},
    )

    # Update user password
    before_snapshot = audit_snapshot("user", user)

    await db.users.update_one(
        {"_id": user_id, "organization_id": org_id},
        {
            "$set": {
                "password_hash": hash_password(new_password),
                "updated_at": now,
            }
        },
    )

    updated_user = await db.users.find_one({"_id": user_id, "organization_id": org_id})
    after_snapshot = audit_snapshot("user", updated_user)

    # Audit log (no raw token)
    try:
        await write_audit_log(
            db,
            organization_id=str(org_id),
            actor={
                "actor_type": "system",
                "actor_id": "password_reset",
                "email": None,
                "roles": [],
            },
            request=request,
            action="password_reset_completed",
            target_type="user",
            target_id=str(user_id),
            before=before_snapshot,
            after=after_snapshot,
            meta={
                "reset_token_fp": _fingerprint_token(token),
                "via": "reset_password_page",
                "organization_id": str(org_id),
                "user_id": str(user_id),
                "agency_id": str(token_doc.get("agency_id")) if token_doc.get("agency_id") else None,
            },
        )
    except Exception:
        # Audit failure must not break main flow
        pass

    return {"status": "ok"}
