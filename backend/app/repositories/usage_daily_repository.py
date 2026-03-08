from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.db import get_db


def _date_key(value: datetime) -> str:
  return value.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _month_bounds(billing_period: str) -> tuple[str, str]:
  year_str, month_str = billing_period.split("-", 1)
  year = int(year_str)
  month = int(month_str)
  last_day = calendar.monthrange(year, month)[1]
  return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def _date_range_keys(start_date: date, end_date: date) -> list[str]:
  keys: list[str] = []
  current = start_date
  while current <= end_date:
    keys.append(current.isoformat())
    current += timedelta(days=1)
  return keys


class UsageDailyRepository:
  async def _col(self):
    db = await get_db()
    return db.usage_daily

  async def increment(
    self,
    *,
    tenant_id: str,
    organization_id: Optional[str],
    metric: str,
    quantity: int,
    event_at: datetime,
  ) -> None:
    col = await self._col()
    now = datetime.now(timezone.utc)
    doc_date = _date_key(event_at)
    set_fields: Dict[str, Any] = {
      "tenant_id": tenant_id,
      "metric": metric,
      "date": doc_date,
      "last_event_at": event_at,
      "updated_at": now,
    }
    if organization_id:
      set_fields["organization_id"] = organization_id

    await col.update_one(
      {"tenant_id": tenant_id, "metric": metric, "date": doc_date},
      {
        "$set": set_fields,
        "$inc": {"count": quantity},
        "$setOnInsert": {"created_at": now},
      },
      upsert=True,
    )

  async def get_period_totals(
    self,
    tenant_id: str,
    billing_period: str,
    organization_id: Optional[str] = None,
  ) -> Dict[str, int]:
    col = await self._col()
    start_date, end_date = _month_bounds(billing_period)
    match: Dict[str, Any] = {
      "tenant_id": tenant_id,
      "date": {"$gte": start_date, "$lte": end_date},
    }
    if organization_id:
      match["organization_id"] = organization_id

    pipeline = [
      {"$match": match},
      {"$group": {"_id": "$metric", "total": {"$sum": "$count"}}},
    ]
    rows = await col.aggregate(pipeline).to_list(length=100)
    return {str(row["_id"]): int(row["total"]) for row in rows}

  async def get_daily_counts(
    self,
    tenant_id: str,
    *,
    start_date: date,
    end_date: date,
    metrics: Optional[list[str]] = None,
    organization_id: Optional[str] = None,
  ) -> Dict[str, Dict[str, int]]:
    col = await self._col()
    match: Dict[str, Any] = {
      "tenant_id": tenant_id,
      "date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()},
    }
    if metrics:
      match["metric"] = {"$in": metrics}
    if organization_id:
      match["organization_id"] = organization_id

    docs = await col.find(match, {"_id": 0, "metric": 1, "date": 1, "count": 1}).to_list(length=5000)
    result: Dict[str, Dict[str, int]] = {}
    for doc in docs:
      metric = str(doc.get("metric") or "")
      doc_date = str(doc.get("date") or "")
      if not metric or not doc_date:
        continue
      result.setdefault(metric, {})[doc_date] = int(doc.get("count") or 0)
    return result

  async def get_zero_filled_daily_counts(
    self,
    tenant_id: str,
    *,
    start_date: date,
    end_date: date,
    metrics: list[str],
    organization_id: Optional[str] = None,
  ) -> Dict[str, list[Dict[str, int | str]]]:
    existing = await self.get_daily_counts(
      tenant_id,
      start_date=start_date,
      end_date=end_date,
      metrics=metrics,
      organization_id=organization_id,
    )
    date_keys = _date_range_keys(start_date, end_date)
    result: Dict[str, list[Dict[str, int | str]]] = {}
    for metric in metrics:
      metric_map = existing.get(metric, {})
      result[metric] = [
        {"date": date_key, "count": int(metric_map.get(date_key, 0))}
        for date_key in date_keys
      ]
    return result

  async def ensure_indexes(self) -> None:
    col = await self._col()
    await col.create_index(
      [("tenant_id", 1), ("metric", 1), ("date", 1)],
      unique=True,
      name="usage_daily_unique_metric_day",
    )
    await col.create_index(
      [("tenant_id", 1), ("date", -1)],
      name="usage_daily_tenant_date_lookup",
    )


usage_daily_repo = UsageDailyRepository()
