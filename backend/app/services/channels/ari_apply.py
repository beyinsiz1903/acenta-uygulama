from __future__ import annotations

from typing import Any, Dict

from pymongo import UpdateOne


async def apply_ari_to_pms(
    *,
    db,
    canonical: Dict[str, Any],
    org_id: str,
    hotel_id: str,
    connector_id: str,
    mode: str,
    dry_run: bool,
    idempotency_key: str,
) -> Dict[str, Any]:
    """Apply canonical ARI to PMS collections (MVP implementation).

    This function is intentionally simple and uses two Mongo collections as
    the "PMS daily" snapshot layer:
      - pms_daily_rates
      - pms_daily_availability

    It returns a dict with keys:
      - status: "success" | "partial" | "failed"
      - summary: {...}
      - diff: {"rates": [...], "availability": [...]} (no old values for now)
    """

    diff: Dict[str, Any] = {"rates": [], "availability": []}
    summary: Dict[str, Any] = {
      "mode": mode,
      "changed_prices": 0,
      "changed_availability": 0,
      "unmapped_rooms": 0,
      "unmapped_rates": 0,
      "skipped": 0,
    }

    rate_writes = []
    avail_writes = []

    # Rates
    for pms_rate_id, obj in (canonical.get("ratePlans") or {}).items():
        for day_str, val in (obj.get("dates") or {}).items():
            price = val.get("price")
            currency = val.get("currency")
            if price is None:
                summary["skipped"] += 1
                continue

            diff["rates"].append(
                {
                    "pms_rate_plan_id": pms_rate_id,
                    "date": day_str,
                    "new": price,
                    "currency": currency,
                }
            )
            rate_writes.append(
                {
                    "organization_id": org_id,
                    "hotel_id": hotel_id,
                    "pms_rate_plan_id": pms_rate_id,
                    "date": day_str,
                    "price": price,
                    "currency": currency,
                    "source": "channel_hub",
                    "connector_id": connector_id,
                    "idempotency_key": idempotency_key,
                }
            )

    # Availability
    for pms_room_id, obj in (canonical.get("roomTypes") or {}).items():
        for day_str, val in (obj.get("dates") or {}).items():
            available = val.get("available")
            stop_sell = val.get("stop_sell")
            if available is None and stop_sell is None:
                summary["skipped"] += 1
                continue

            diff["availability"].append(
                {
                    "pms_room_type_id": pms_room_id,
                    "date": day_str,
                    "new": {"available": available, "stop_sell": stop_sell},
                }
            )
            avail_writes.append(
                {
                    "organization_id": org_id,
                    "hotel_id": hotel_id,
                    "pms_room_type_id": pms_room_id,
                    "date": day_str,
                    "available": available,
                    "stop_sell": stop_sell,
                    "source": "channel_hub",
                    "connector_id": connector_id,
                    "idempotency_key": idempotency_key,
                }
            )

    summary["changed_prices"] = len(rate_writes)
    summary["changed_availability"] = len(avail_writes)

    if dry_run:
        return {"status": "success", "summary": summary, "diff": diff}

    # Persist to Mongo as upserted snapshot rows
    try:
        if rate_writes:
            rate_ops = [
                UpdateOne(
                    {
                        "organization_id": org_id,
                        "hotel_id": hotel_id,
                        "pms_rate_plan_id": r["pms_rate_plan_id"],
                        "date": r["date"],
                    },
                    {"$set": r},
                    upsert=True,
                )
                for r in rate_writes
            ]
            await db.pms_daily_rates.bulk_write(rate_ops, ordered=False)

        if avail_writes:
            avail_ops = [
                UpdateOne(
                    {
                        "organization_id": org_id,
                        "hotel_id": hotel_id,
                        "pms_room_type_id": a["pms_room_type_id"],
                        "date": a["date"],
                    },
                    {"$set": a},
                    upsert=True,
                )
                for a in avail_writes
            ]
            await db.pms_daily_availability.bulk_write(avail_ops, ordered=False)

    except Exception:
        # For MVP we simply mark status as failed; callers wrap this in try/except
        return {"status": "failed", "summary": summary, "diff": diff}

    return {"status": "success", "summary": summary, "diff": diff}
