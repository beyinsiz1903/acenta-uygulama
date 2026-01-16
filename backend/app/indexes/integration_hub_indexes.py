from __future__ import annotations

from pymongo import ASCENDING


async def ensure_integration_hub_indexes(db):
    async def _safe_create(collection, *args, **kwargs):
        try:
            await collection.create_index(*args, **kwargs)
        except Exception:
            return

    await _safe_create(
        db.integration_providers,
        [("key", ASCENDING)],
        name="providers_by_key",
        unique=True,
    )

    await _safe_create(
        db.integration_provider_credentials,
        [("organization_id", ASCENDING), ("provider_key", ASCENDING)],
        name="provider_credentials_by_org_provider",
    )

    await _safe_create(
        db.integration_mappings,
        [
            ("organization_id", ASCENDING),
            ("provider_key", ASCENDING),
            ("mapping_type", ASCENDING),
            ("internal_id", ASCENDING),
        ],
        name="integration_mappings_by_org_provider_type_internal",
        unique=True,
    )
