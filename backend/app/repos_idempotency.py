from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from pymongo.errors import DuplicateKeyError

from app.errors import AppError
from app.idempotency_hash import compute_request_hash
from app.utils import now_utc

DEFAULT_TTL_HOURS = 24


class IdempotencyRepo:
    def __init__(self, db):
        self.col = db.idempotency_keys

    async def get(
        self,
        org_id: str,
        agency_id: str,
        endpoint: str,
        key: str,
    ) -> Optional[Dict[str, Any]]:
        return await self.col.find_one(
            {
                "organization_id": org_id,
                "agency_id": agency_id,
                "endpoint": endpoint,
                "key": key,
            }
        )

    async def store_or_replay(
        self,
        *,
        org_id: str,
        agency_id: str,
        endpoint: str,
        key: str,
        method: str,
        path: str,
        request_body: Dict[str, Any],
        compute_response_fn,  # async callable returning (status_code:int, response_body:dict)
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ) -> Tuple[int, Dict[str, Any]]:
        req_hash = compute_request_hash(method, path, request_body)

        existing = await self.get(org_id, agency_id, endpoint, key)
        if existing:
            if existing.get("request_hash") != req_hash:
                raise AppError(
                    409,
                    "idempotency_key_reused",
                    "Idempotency-Key was already used with a different request payload",
                    {"key": key, "endpoint": endpoint},
                )
            return existing.get("status_code", 200), existing["response_snapshot"]

        # compute fresh
        status_code, response_body = await compute_response_fn()

        now = now_utc()
        doc = {
            "organization_id": org_id,
            "agency_id": agency_id,
            "endpoint": endpoint,
            "key": key,
            "request_hash": req_hash,
            "response_snapshot": response_body,
            "status_code": status_code,
            "created_at": now,
            "expires_at": now + timedelta(hours=ttl_hours),
            "status": "stored",
        }

        try:
            await self.col.insert_one(doc)
            return status_code, response_body
        except DuplicateKeyError:
            # race: another worker wrote it first
            existing = await self.get(org_id, agency_id, endpoint, key)
            if not existing:
                raise AppError(500, "internal_error", "Idempotency storage race condition")
            if existing.get("request_hash") != req_hash:
                raise AppError(
                    409,
                    "idempotency_key_reused",
                    "Idempotency-Key was already used with a different request payload",
                    {"key": key, "endpoint": endpoint},
                )
            return existing.get("status_code", 200), existing["response_snapshot"]


async def ensure_idempotency_indexes(db) -> None:
    await db.idempotency_keys.create_index(
        [
            ("organization_id", 1),
            ("agency_id", 1),
            ("endpoint", 1),
            ("key", 1),
        ],
        unique=True,
        name="uniq_idem_key",
    )
    await db.idempotency_keys.create_index(
        [("expires_at", 1)], expireAfterSeconds=0, name="ttl_idem_expires"
    )
