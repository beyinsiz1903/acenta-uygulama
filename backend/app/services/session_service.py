from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.db import get_db
from app.repositories.session_repository import SessionRepository


def _repo(db) -> SessionRepository:
    return SessionRepository(db)


async def create_session(
    *,
    user_id: str,
    user_email: str,
    organization_id: str,
    roles: list[str],
    user_agent: str = "",
    ip_address: str = "",
) -> dict[str, Any]:
    db = await get_db()
    repo = _repo(db)
    now = datetime.now(timezone.utc)
    doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_email": user_email,
        "organization_id": organization_id,
        "roles": roles,
        "user_agent": user_agent[:500] if user_agent else "",
        "ip_address": ip_address,
        "created_at": now,
        "updated_at": now,
        "last_seen_at": now,
        "revoked_at": None,
        "revoke_reason": None,
        "current_refresh_family_id": None,
    }
    return await repo.create(doc)


async def get_active_session(session_id: str) -> Optional[dict[str, Any]]:
    db = await get_db()
    repo = _repo(db)
    return await repo.get_active_by_id(session_id)


async def list_active_sessions(user_email: str) -> list[dict[str, Any]]:
    db = await get_db()
    repo = _repo(db)
    docs = await repo.list_active_for_user(user_email)
    return [
        {
            "id": d["_id"],
            "user_agent": d.get("user_agent", ""),
            "ip_address": d.get("ip_address", ""),
            "created_at": d.get("created_at"),
            "last_used_at": d.get("last_seen_at"),
        }
        for d in docs
    ]


async def revoke_session(session_id: str, reason: str = "logout") -> bool:
    db = await get_db()
    repo = _repo(db)
    return await repo.revoke_by_id(session_id, reason)


async def revoke_all_sessions(user_email: str, reason: str = "user_revoke_all") -> int:
    db = await get_db()
    repo = _repo(db)
    return await repo.revoke_for_user(user_email, reason)


async def update_session_last_seen(session_id: str) -> None:
    db = await get_db()
    repo = _repo(db)
    await repo.update_last_seen(session_id)


async def set_session_refresh_family(session_id: str, family_id: str) -> None:
    db = await get_db()
    repo = _repo(db)
    await repo.set_refresh_family(session_id, family_id)


async def ensure_session_indexes() -> None:
    db = await get_db()
    repo = _repo(db)
    await repo.ensure_indexes()