"""TenantScopedRepository — enforced multi-tenant data access layer.

ALL tenant-scoped database operations MUST go through this base class.
Direct collection access (db.bookings.find()) is prohibited for tenant data.

Key guarantees:
- Every query includes organization_id filter (cannot be bypassed)
- Aggregate pipelines start with $match: {organization_id: ...}
- Insert operations automatically stamp organization_id
- No legacy fallback: missing organization_id = hard error
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.modules.tenant.context import TenantContext
from app.modules.tenant.errors import (
    TenantContextMissing,
    TenantFilterBypassAttempt,
)

logger = logging.getLogger("tenant.repository")


class TenantScopedRepository:
    """Base class for all tenant-aware repositories.

    Subclasses define ``collection_name`` and inherit safe CRUD methods.
    The org_id filter is injected into every operation — no exceptions.

    Usage:
        class BookingRepo(TenantScopedRepository):
            collection_name = "bookings"

        repo = BookingRepo(db, tenant_ctx)
        doc = await repo.find_one({"status": "confirmed"})
    """

    collection_name: str = ""  # override in subclass

    def __init__(self, db: AsyncIOMotorDatabase, ctx: TenantContext) -> None:
        if not self.collection_name:
            raise ValueError(f"{self.__class__.__name__} must define collection_name")
        self._db = db
        self._ctx = ctx
        self._col: AsyncIOMotorCollection = db[self.collection_name]

    @property
    def org_id(self) -> str:
        return self._ctx.org_id

    @property
    def tenant_id(self) -> str:
        return self._ctx.tenant_id

    def _scoped(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Inject organization_id into query. Raises if org_id is empty."""
        if not self.org_id:
            raise TenantContextMissing(
                f"organization_id is required for {self.collection_name} queries"
            )
        base = dict(query or {})
        if "organization_id" in base and base["organization_id"] != self.org_id:
            raise TenantFilterBypassAttempt(
                f"Cross-tenant access attempt on {self.collection_name}: "
                f"context org={self.org_id}, query org={base['organization_id']}"
            )
        base["organization_id"] = self.org_id
        return base

    def _scope_pipeline(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure aggregate pipeline starts with org_id match."""
        if not self.org_id:
            raise TenantContextMissing(
                f"organization_id is required for {self.collection_name} aggregation"
            )
        tenant_match = {"$match": {"organization_id": self.org_id}}

        if not pipeline:
            return [tenant_match]

        first_stage = pipeline[0]
        if "$match" in first_stage:
            existing_match = first_stage["$match"]
            if "organization_id" in existing_match:
                if existing_match["organization_id"] != self.org_id:
                    raise TenantFilterBypassAttempt(
                        f"Cross-tenant aggregation on {self.collection_name}"
                    )
                return pipeline
            merged = {**existing_match, "organization_id": self.org_id}
            return [{"$match": merged}] + pipeline[1:]

        return [tenant_match] + pipeline

    # ── READ ──────────────────────────────────────────────

    async def find_one(
        self,
        query: dict[str, Any] | None = None,
        projection: dict[str, Any] | None = None,
    ) -> Optional[dict[str, Any]]:
        return await self._col.find_one(self._scoped(query), projection)

    async def find_many(
        self,
        query: dict[str, Any] | None = None,
        projection: dict[str, Any] | None = None,
        sort: list | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        cursor = self._col.find(self._scoped(query), projection)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        cursor = cursor.limit(limit)
        return await cursor.to_list(limit)

    async def count(self, query: dict[str, Any] | None = None) -> int:
        return await self._col.count_documents(self._scoped(query))

    async def distinct(
        self,
        field: str,
        query: dict[str, Any] | None = None,
    ) -> list[Any]:
        return await self._col.distinct(field, self._scoped(query))

    async def aggregate(
        self,
        pipeline: list[dict[str, Any]],
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        scoped = self._scope_pipeline(pipeline)
        return await self._col.aggregate(scoped).to_list(limit)

    # ── WRITE ─────────────────────────────────────────────

    async def insert_one(self, doc: dict[str, Any]) -> str:
        """Insert document with enforced organization_id."""
        if not self.org_id:
            raise TenantContextMissing("organization_id required for insert")
        doc["organization_id"] = self.org_id
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def insert_many(self, docs: list[dict[str, Any]]) -> list[str]:
        if not self.org_id:
            raise TenantContextMissing("organization_id required for insert_many")
        for doc in docs:
            doc["organization_id"] = self.org_id
        result = await self._col.insert_many(docs)
        return [str(oid) for oid in result.inserted_ids]

    async def update_one(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
    ) -> int:
        """Update one document within tenant scope. Returns modified count."""
        result = await self._col.update_one(
            self._scoped(query), update, upsert=upsert
        )
        return result.modified_count

    async def update_many(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
    ) -> int:
        result = await self._col.update_many(self._scoped(query), update)
        return result.modified_count

    async def find_one_and_update(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        return_document: bool = True,
        upsert: bool = False,
    ) -> Optional[dict[str, Any]]:
        from pymongo import ReturnDocument

        return await self._col.find_one_and_update(
            self._scoped(query),
            update,
            return_document=ReturnDocument.AFTER if return_document else ReturnDocument.BEFORE,
            upsert=upsert,
        )

    # ── DELETE ────────────────────────────────────────────

    async def delete_one(self, query: dict[str, Any]) -> int:
        result = await self._col.delete_one(self._scoped(query))
        return result.deleted_count

    async def delete_many(self, query: dict[str, Any]) -> int:
        result = await self._col.delete_many(self._scoped(query))
        return result.deleted_count
