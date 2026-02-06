"""Runtime feature flags stored in DB (not env vars).

Collection: runtime_config
Schema: { key: str (unique), value: any, updated_at }
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.db import get_db


async def get_config(key: str, default: Any = None) -> Any:
  """Get a runtime config value."""
  db = await get_db()
  doc = await db.runtime_config.find_one({"key": key})
  if doc is None:
    return default
  return doc.get("value", default)


async def set_config(key: str, value: Any) -> None:
  """Set a runtime config value."""
  db = await get_db()
  await db.runtime_config.update_one(
    {"key": key},
    {"$set": {"key": key, "value": value, "updated_at": datetime.now(timezone.utc)}},
    upsert=True,
  )


# Overage billing config keys
OVERAGE_ENABLED_KEY = "overage_billing_enabled"  # bool: false=shadow, true=real
OVERAGE_PRICE_PER_UNIT_KEY = "overage_price_per_unit"  # int: kuruş (e.g., 700 = ₺7)
OVERAGE_MODE_KEY = "overage_billing_mode"  # str: "shadow" | "new_only" | "opt_in" | "all"


async def is_overage_enabled() -> bool:
  return bool(await get_config(OVERAGE_ENABLED_KEY, False))


async def get_overage_mode() -> str:
  return str(await get_config(OVERAGE_MODE_KEY, "shadow"))


async def get_overage_price_per_unit() -> Optional[int]:
  """Returns price in kuruş (e.g., 700 = ₺7.00). None if not set."""
  val = await get_config(OVERAGE_PRICE_PER_UNIT_KEY)
  return int(val) if val is not None else None
