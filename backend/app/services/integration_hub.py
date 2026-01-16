from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.services.jobs import register_job_handler, enqueue_job


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Collections helpers
# ---------------------------------------------------------------------------


async def list_providers(db) -> List[Dict[str, Any]]:
    docs = await db.integration_providers.find({}, {"_id": 0}).to_list(1000)
    return docs


async def upsert_provider(db, payload: Dict[str, Any]) -> Dict[str, Any]:
    key = payload["key"]
    now = _now()
    await db.integration_providers.update_one(
        {"key": key},
        {
            "$set": {
                "name": payload.get("name"),
                "category": payload.get("category"),
                "capabilities": payload.get("capabilities") or [],
                "updated_at": now,
            },
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )
    doc = await db.integration_providers.find_one({"key": key}, {"_id": 0})
    return doc or {}


async def list_credentials(db, organization_id: str) -> List[Dict[str, Any]]:
    docs = await db.integration_provider_credentials.find(
        {"organization_id": organization_id}, {"_id": 0}
    ).to_list(1000)
    return docs


async def upsert_credentials(db, organization_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = _now()
    provider_key = payload["provider_key"]
    name = payload.get("name") or provider_key
    status = payload.get("status") or "active"
    config = payload.get("config") or {}

    await db.integration_provider_credentials.update_one(
        {"organization_id": organization_id, "provider_key": provider_key, "name": name},
        {
            "$set": {
                "status": status,
                "config": config,
                "updated_at": now,
            },
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )

    doc = await db.integration_provider_credentials.find_one(
        {"organization_id": organization_id, "provider_key": provider_key, "name": name},
        {"_id": 0},
    )
    return doc or {}


async def list_mappings(db, organization_id: str, provider_key: Optional[str] = None) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {"organization_id": organization_id}
    if provider_key:
        q["provider_key"] = provider_key
    docs = await db.integration_mappings.find(q, {"_id": 0}).to_list(2000)
    return docs


async def upsert_mapping(db, organization_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = _now()
    provider_key = payload["provider_key"]
    mapping_type = payload["mapping_type"]
    internal_id = payload["internal_id"]
    external_id = payload["external_id"]
    meta = payload.get("meta") or {}

    await db.integration_mappings.update_one(
        {
            "organization_id": organization_id,
            "provider_key": provider_key,
            "mapping_type": mapping_type,
            "internal_id": internal_id,
        },
        {
            "$set": {
                "external_id": external_id,
                "meta": meta,
                "updated_at": now,
            },
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )

    doc = await db.integration_mappings.find_one(
        {
            "organization_id": organization_id,
            "provider_key": provider_key,
            "mapping_type": mapping_type,
            "internal_id": internal_id,
        },
        {"_id": 0},
    )
    return doc or {}


# ---------------------------------------------------------------------------
# Provider adapter registry (mock-only for V1)
# ---------------------------------------------------------------------------


class ProviderAdapter:
    async def healthcheck(self, db, *, organization_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    async def sync_availability(
        self,
        db,
        *,
        organization_id: str,
        credentials: Dict[str, Any],
        mappings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    async def sync_rates(
        self,
        db,
        *,
        organization_id: str,
        credentials: Dict[str, Any],
        mappings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError


class MockHotelProvider(ProviderAdapter):
    """Deterministic mock provider used for Integration Hub V1.

    - Does NOT call any external API
    - Reads mappings and touches rate_plans for simple proof-of-life
    """

    async def healthcheck(self, db, *, organization_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True, "organization_id": organization_id, "provider": "mock_hotel_provider"}

    async def sync_availability(
        self,
        db,
        *,
        organization_id: str,
        credentials: Dict[str, Any],
        mappings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # For V1 we only simulate success and count mappings
        return {"ok": True, "synced": len(mappings)}

    async def sync_rates(
        self,
        db,
        *,
        organization_id: str,
        credentials: Dict[str, Any],
        mappings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # Bump a simple field on rate_plans as deterministic side effect
        updated = 0
        for m in mappings:
            if m.get("mapping_type") != "rate_plan":
                continue
            internal_id = m.get("internal_id")
            if not internal_id:
                continue
            res = await db.rate_plans.update_one(
                {"organization_id": organization_id, "_id": internal_id},
                {"$set": {"last_mock_sync_at": _now()}},
            )
            if res.matched_count:
                updated += 1
        return {"ok": True, "updated_rate_plans": updated}


PROVIDER_ADAPTERS: Dict[str, ProviderAdapter] = {"mock_hotel_provider": MockHotelProvider()}


async def get_adapter(provider_key: str) -> ProviderAdapter:
    adapter = PROVIDER_ADAPTERS.get(provider_key)
    if not adapter:
        raise KeyError(f"No adapter registered for provider_key={provider_key}")
    return adapter


# ---------------------------------------------------------------------------
# Job handlers registration (integration.* job types)
# ---------------------------------------------------------------------------


INTEGRATION_SYNC_AVAILABILITY = "integration.sync_availability"
INTEGRATION_SYNC_RATES = "integration.sync_rates"


async def handle_integration_sync_availability(db, job: Dict[str, Any]) -> None:
    payload = job.get("payload") or {}
    org_id = payload.get("organization_id") or job.get("organization_id")
    provider_key = payload.get("provider_key") or "mock_hotel_provider"

    adapter = await get_adapter(provider_key)

    creds = await db.integration_provider_credentials.find_one(
        {"organization_id": org_id, "provider_key": provider_key},
        {"_id": 0},
    )
    mappings = await db.integration_mappings.find(
        {"organization_id": org_id, "provider_key": provider_key},
        {"_id": 0},
    ).to_list(2000)

    await adapter.sync_availability(db, organization_id=org_id, credentials=creds or {}, mappings=mappings)


async def handle_integration_sync_rates(db, job: Dict[str, Any]) -> None:
    payload = job.get("payload") or {}
    org_id = payload.get("organization_id") or job.get("organization_id")
    provider_key = payload.get("provider_key") or "mock_hotel_provider"

    adapter = await get_adapter(provider_key)

    creds = await db.integration_provider_credentials.find_one(
        {"organization_id": org_id, "provider_key": provider_key},
        {"_id": 0},
    )
    mappings = await db.integration_mappings.find(
        {"organization_id": org_id, "provider_key": provider_key},
        {"_id": 0},
    ).to_list(2000)

    await adapter.sync_rates(db, organization_id=org_id, credentials=creds or {}, mappings=mappings)


def register_integration_job_handlers() -> None:
    register_job_handler(INTEGRATION_SYNC_AVAILABILITY, handle_integration_sync_availability)
    register_job_handler(INTEGRATION_SYNC_RATES, handle_integration_sync_rates)


async def enqueue_sync_jobs_for_provider(
    *,
    organization_id: str,
    provider_key: str,
    scope: str,
) -> int:
    """Enqueue integration sync jobs for given provider/org.

    scope: "availability" | "rates" | "both"
    """

    db = await get_db()
    job_type_keys: List[str] = []
    if scope in ("availability", "both"):
        job_type_keys.append(INTEGRATION_SYNC_AVAILABILITY)
    if scope in ("rates", "both"):
        job_type_keys.append(INTEGRATION_SYNC_RATES)

    count = 0
    for job_type in job_type_keys:
        await enqueue_job(
            db,
            organization_id=organization_id,
            type=job_type,
            payload={"organization_id": organization_id, "provider_key": provider_key},
            max_attempts=3,
        )
        count += 1
    return count
