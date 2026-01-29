from __future__ import annotations

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection


def get_collection(db: AsyncIOMotorDatabase, name: str) -> AsyncIOMotorCollection:
    """Return a Motor collection from the given database.

    This is the only place where services should obtain collections.
    """

    return db[name]


def with_org_filter(filter_dict: Dict[str, Any], organization_id: str) -> Dict[str, Any]:
    """Inject organization_id into a Mongo filter dict.

    Ensures that all multi-tenant queries are scoped by organization_id.
    """

    if not organization_id:
        raise ValueError("organization_id is required for org-scoped queries")

    f = dict(filter_dict or {})
    # Do not overwrite if explicitly set, but normally it should not be
    f.setdefault("organization_id", organization_id)
    return f
