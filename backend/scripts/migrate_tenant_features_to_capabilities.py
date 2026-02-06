"""Migration: tenant_features → tenant_capabilities

Reads all docs from tenant_features and upserts into tenant_capabilities.
Existing tenant_capabilities docs are NOT overwritten.

Usage:
  cd /app/backend && python scripts/migrate_tenant_features_to_capabilities.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from motor.motor_asyncio import AsyncIOMotorClient

from app.constants.plan_matrix import DEFAULT_PLAN


async def main():
  mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
  db_name = os.environ.get("DB_NAME", "test_database")

  client = AsyncIOMotorClient(mongo_url)
  db = client[db_name]

  migrated = 0
  skipped = 0

  cursor = db.tenant_features.find({})
  async for doc in cursor:
    tenant_id = doc.get("tenant_id")
    if not tenant_id:
      skipped += 1
      continue

    existing = await db.tenant_capabilities.find_one({"tenant_id": tenant_id})
    if existing:
      print(f"  SKIP {tenant_id} (already in tenant_capabilities)")
      skipped += 1
      continue

    plan = doc.get("plan") or DEFAULT_PLAN
    features = list(doc.get("features") or [])

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    await db.tenant_capabilities.update_one(
      {"tenant_id": tenant_id},
      {
        "$set": {
          "tenant_id": tenant_id,
          "plan": plan,
          "add_ons": features,
          "updated_at": now,
        },
        "$setOnInsert": {"created_at": now},
      },
      upsert=True,
    )
    migrated += 1
    print(f"  MIGRATED {tenant_id} plan={plan} add_ons={features}")

  # Ensure unique index
  await db.tenant_capabilities.create_index("tenant_id", unique=True)

  print(f"\nDone: migrated={migrated}, skipped={skipped}")
  client.close()


if __name__ == "__main__":
  asyncio.run(main())
