"""Hotel Portfolio Sync Engine.

Handles multi-hotel, multi-sheet sync with:
- Lock-based concurrency control
- SHA256 fingerprinting for delta detection
- On-demand + scheduled sync
- Graceful fallback when provider not configured
- Tenant isolation
- Audit logging
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.services.sheets_provider import (
    get_fingerprint as provider_get_fingerprint,
    is_configured,
    read_sheet,
)

logger = logging.getLogger(__name__)

HEADER_ALIASES = {
    "date": ["tarih", "date", "gun", "checkin", "check_in", "check-in", "giris"],
    "room_type": ["oda_tipi", "room_type", "room", "oda", "type", "tip"],
    "price": ["fiyat", "price", "tl", "amount", "ucret", "tutar", "rate"],
    "allotment": ["kontenjan", "allotment", "stok", "qty", "adet", "musaitlik", "availability"],
    "stop_sale": ["stop_sale", "stop", "kapali", "closed", "satis_durdur"],
    "hotel_name": ["otel", "hotel", "otel_adi", "hotel_name", "name", "ad"],
    "city": ["sehir", "city", "il", "bolge", "location"],
    "country": ["ulke", "country"],
    "description": ["aciklama", "description", "desc", "not"],
    "stars": ["yildiz", "stars", "star", "kategori"],
    "phone": ["telefon", "phone", "tel"],
    "email": ["email", "e-posta", "eposta", "mail"],
    "address": ["adres", "address"],
    "image_url": ["resim", "image", "image_url", "foto", "gorsel"],
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Auto-detect Mapping ──────────────────────────────────────

def auto_detect_mapping(headers: List[str]) -> Dict[str, str]:
    """Auto-detect column mapping from headers using fuzzy matching.

    Returns dict: {header_name: canonical_field_name}
    """
    mapping = {}
    normalized_headers = [h.lower().strip().replace(" ", "_") for h in headers]

    for field, aliases in HEADER_ALIASES.items():
        for i, nh in enumerate(normalized_headers):
            if nh in aliases or any(a in nh for a in aliases):
                mapping[headers[i]] = field
                break

    return mapping


def apply_mapping(
    headers: List[str],
    rows: List[List[str]],
    mapping: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Apply column mapping to rows.

    mapping: {header_name: field_name}
    Returns list of dicts with canonical field names.
    """
    header_to_idx = {h: i for i, h in enumerate(headers)}
    result = []
    for row_num, row in enumerate(rows, start=2):
        record: Dict[str, Any] = {"_row_number": row_num}
        for header_name, field_name in mapping.items():
            if field_name == "ignore":
                continue
            idx = header_to_idx.get(header_name)
            if idx is not None and idx < len(row):
                record[field_name] = row[idx].strip()
        result.append(record)
    return result


# ── Fingerprinting ─────────────────────────────────────────

def fingerprint_row(mapped_row: Dict[str, Any]) -> str:
    """SHA256 of sorted JSON fields (excluding internal keys)."""
    clean = {k: v for k, v in mapped_row.items() if not k.startswith("_")}
    canonical = json.dumps(clean, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_row_key(hotel_id: str, row_number: int) -> str:
    return f"{hotel_id}|row|{row_number}"


# ── Lock Management ────────────────────────────────────────

async def acquire_sync_lock(
    db, tenant_id: str, hotel_id: str, ttl_minutes: int = 10
) -> bool:
    """Try to acquire a sync lock. Returns True if acquired."""
    now = _now()
    expiry = now + timedelta(minutes=ttl_minutes)
    lock_key = f"{tenant_id}:{hotel_id}"

    try:
        result = await db.sheet_sync_locks.update_one(
            {
                "lock_key": lock_key,
                "$or": [
                    {"expires_at": {"$lt": now}},
                    {"expires_at": {"$exists": False}},
                ],
            },
            {
                "$set": {"expires_at": expiry, "locked_at": now},
                "$setOnInsert": {
                    "_id": str(uuid.uuid4()),
                    "lock_key": lock_key,
                    "tenant_id": tenant_id,
                    "hotel_id": hotel_id,
                },
            },
            upsert=True,
        )
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception:
        return False


async def release_sync_lock(db, tenant_id: str, hotel_id: str) -> None:
    lock_key = f"{tenant_id}:{hotel_id}"
    await db.sheet_sync_locks.delete_one({"lock_key": lock_key})


# ── Delta Detection ───────────────────────────────────────

async def compute_delta(
    db,
    tenant_id: str,
    hotel_id: str,
    mapped_rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int]:
    """Filter out rows that haven't changed since last sync.

    Returns (changed_rows, skipped_count).
    """
    changed = []
    skipped = 0

    for row in mapped_rows:
        row_num = row.get("_row_number", 0)
        row_key = make_row_key(hotel_id, row_num)
        fp = fingerprint_row(row)

        existing = await db.sheet_row_fingerprints.find_one({
            "tenant_id": tenant_id,
            "hotel_id": hotel_id,
            "row_key": row_key,
        })

        if existing and existing.get("fingerprint") == fp:
            skipped += 1
            continue

        await db.sheet_row_fingerprints.update_one(
            {
                "tenant_id": tenant_id,
                "hotel_id": hotel_id,
                "row_key": row_key,
            },
            {
                "$set": {"fingerprint": fp, "updated_at": _now()},
                "$setOnInsert": {"_id": str(uuid.uuid4())},
            },
            upsert=True,
        )
        changed.append(row)

    return changed, skipped


# ── Upsert Inventory ──────────────────────────────────────

async def upsert_inventory_rows(
    db,
    tenant_id: str,
    hotel_id: str,
    rows: List[Dict[str, Any]],
    source: str = "sheet_sync",
) -> Tuple[int, int, List[Dict[str, Any]]]:
    """Upsert inventory/pricing rows from sheet.

    Upserts to hotel_inventory_snapshots collection.
    Returns (upsert_count, error_count, errors).
    """
    now = _now()
    upserts = 0
    errors_list: List[Dict[str, Any]] = []

    for row in rows:
        row_num = row.pop("_row_number", 0)
        try:
            date_str = (row.get("date") or "").strip()
            room_type = (row.get("room_type") or "standard").strip()
            price_str = (row.get("price") or "").strip()
            allotment_str = (row.get("allotment") or "").strip()
            stop_sale = (row.get("stop_sale") or "").strip().lower() in (
                "true", "1", "yes", "evet", "kapali"
            )

            update_fields: Dict[str, Any] = {
                "updated_at": now,
                "updated_by": source,
                "source": source,
            }

            if date_str:
                update_fields["date"] = date_str
            if room_type:
                update_fields["room_type"] = room_type
            if price_str:
                try:
                    update_fields["price"] = float(price_str.replace(",", ".").replace(" ", ""))
                except (ValueError, TypeError):
                    pass
            if allotment_str:
                try:
                    update_fields["allotment"] = int(float(allotment_str.replace(",", ".").replace(" ", "")))
                except (ValueError, TypeError):
                    pass
            update_fields["stop_sale"] = stop_sale

            # Also upsert hotel-level data if present
            hotel_update = {}
            for f in ["hotel_name", "city", "country", "description", "stars", "phone", "email", "address", "image_url"]:
                if row.get(f):
                    hotel_update[f] = row[f].strip()

            # Upsert to inventory snapshots
            filter_key = {
                "tenant_id": tenant_id,
                "hotel_id": hotel_id,
            }
            if date_str:
                filter_key["date"] = date_str
            if room_type:
                filter_key["room_type"] = room_type

            await db.hotel_inventory_snapshots.update_one(
                filter_key,
                {
                    "$set": update_fields,
                    "$setOnInsert": {
                        "_id": str(uuid.uuid4()),
                        "tenant_id": tenant_id,
                        "hotel_id": hotel_id,
                        "created_at": now,
                    },
                },
                upsert=True,
            )

            # Also update hotel record if hotel-level data present
            if hotel_update:
                hotel_set = {"updated_at": now}
                for k, v in hotel_update.items():
                    if k == "hotel_name":
                        hotel_set["name"] = v
                    elif k == "stars":
                        try:
                            hotel_set["stars"] = int(v)
                        except (ValueError, TypeError):
                            pass
                    elif k == "price" and not date_str:
                        try:
                            hotel_set["base_price"] = float(v.replace(",", "."))
                        except (ValueError, TypeError):
                            pass
                    else:
                        hotel_set[k] = v
                await db.hotels.update_one(
                    {"_id": hotel_id},
                    {"$set": hotel_set},
                )

            upserts += 1
        except Exception as e:
            errors_list.append({"row_number": row_num, "error": str(e)})

    return upserts, len(errors_list), errors_list


# ── Full Sync Run ─────────────────────────────────────────

async def run_hotel_sheet_sync(
    db,
    connection: Dict[str, Any],
    trigger: str = "manual",
) -> Dict[str, Any]:
    """Execute a full sync cycle for a hotel sheet connection.

    Steps: lock -> fetch -> map -> fingerprint -> delta -> upsert -> log -> unlock
    Returns sync run summary.
    """
    conn_id = connection["_id"]
    tenant_id = connection["tenant_id"]
    hotel_id = connection["hotel_id"]
    sheet_id = connection["sheet_id"]
    tab = connection.get("sheet_tab", "Sheet1")
    mapping = connection.get("mapping", {})

    run_id = str(uuid.uuid4())
    run_doc = {
        "_id": run_id,
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
        "connection_id": conn_id,
        "sheet_id": sheet_id,
        "trigger": trigger,
        "started_at": _now(),
        "finished_at": None,
        "status": "running",
        "rows_read": 0,
        "rows_changed": 0,
        "upserted": 0,
        "skipped": 0,
        "errors_count": 0,
        "errors": [],
        "duration_ms": 0,
    }
    await db.sheet_sync_runs.insert_one(run_doc)

    start_time = _now()

    # 1. Acquire lock
    if not await acquire_sync_lock(db, tenant_id, hotel_id):
        run_doc["status"] = "skipped"
        run_doc["errors"] = [{"message": "Sync lock alinaamadi - baska bir sync devam ediyor"}]
        run_doc["finished_at"] = _now()
        await db.sheet_sync_runs.update_one({"_id": run_id}, {"$set": run_doc})
        return run_doc

    try:
        # 2. Check if configured
        if not is_configured():
            run_doc["status"] = "not_configured"
            run_doc["errors"] = [{"message": "Google Sheets yapilandirilmamis"}]
            run_doc["finished_at"] = _now()
            await _update_connection_status(db, conn_id, "not_configured", "Google Sheets yapilandirilmamis")
            await db.sheet_sync_runs.update_one({"_id": run_id}, {"$set": run_doc})
            return run_doc

        # 3. Check fingerprint for early exit
        fp_result = provider_get_fingerprint(sheet_id, tab)
        if fp_result.success:
            new_fp = fp_result.data.get("fingerprint", "")
            old_fp = connection.get("last_fingerprint", "")
            if new_fp and old_fp and new_fp == old_fp:
                run_doc["status"] = "no_change"
                run_doc["finished_at"] = _now()
                run_doc["duration_ms"] = int((_now() - start_time).total_seconds() * 1000)
                await db.hotel_portfolio_sources.update_one(
                    {"_id": conn_id},
                    {"$set": {"last_sync_at": _now(), "last_sync_status": "no_change", "updated_at": _now()}},
                )
                await db.sheet_sync_runs.update_one({"_id": run_id}, {"$set": run_doc})
                return run_doc

        # 4. Fetch data
        sheet_result = read_sheet(sheet_id, tab)
        if not sheet_result.success:
            run_doc["status"] = "failed"
            run_doc["errors"] = [{"message": sheet_result.error or "Sheet okuma hatasi"}]
            run_doc["finished_at"] = _now()
            await _update_connection_status(db, conn_id, "error", sheet_result.error)
            await db.sheet_sync_runs.update_one({"_id": run_id}, {"$set": run_doc})
            return run_doc

        headers = sheet_result.data.get("headers", [])
        rows = sheet_result.data.get("rows", [])
        run_doc["rows_read"] = len(rows)

        if not rows:
            run_doc["status"] = "success"
            run_doc["finished_at"] = _now()
            run_doc["duration_ms"] = int((_now() - start_time).total_seconds() * 1000)
            await _update_connection_status(db, conn_id, "success", None)
            await db.sheet_sync_runs.update_one({"_id": run_id}, {"$set": run_doc})
            return run_doc

        # 5. Apply mapping (auto-detect if no saved mapping)
        effective_mapping = mapping
        if not effective_mapping:
            effective_mapping = auto_detect_mapping(headers)

        mapped = apply_mapping(headers, rows, effective_mapping)

        # 6. Delta detection
        changed, skipped = await compute_delta(db, tenant_id, hotel_id, mapped)
        run_doc["rows_changed"] = len(changed)
        run_doc["skipped"] = skipped

        # 7. Upsert
        if changed:
            upsert_count, err_count, upsert_errors = await upsert_inventory_rows(
                db, tenant_id, hotel_id, changed
            )
            run_doc["upserted"] = upsert_count
            run_doc["errors_count"] = err_count
            run_doc["errors"] = upsert_errors[:20]
        else:
            run_doc["upserted"] = 0

        # 8. Update connection
        run_doc["status"] = "success" if run_doc["errors_count"] == 0 else "partial"
        run_doc["finished_at"] = _now()
        run_doc["duration_ms"] = int((_now() - start_time).total_seconds() * 1000)

        update_data = {
            "last_sync_at": _now(),
            "last_sync_status": run_doc["status"],
            "last_error": None if run_doc["status"] == "success" else str(run_doc.get("errors", [])),
            "updated_at": _now(),
        }
        if fp_result.success:
            update_data["last_fingerprint"] = fp_result.data.get("fingerprint", "")

        await db.hotel_portfolio_sources.update_one(
            {"_id": conn_id},
            {"$set": update_data},
        )

    except Exception as e:
        logger.error("Sheet sync failed for hotel %s: %s", hotel_id, e)
        run_doc["status"] = "failed"
        run_doc["errors"] = [{"message": str(e)}]
        run_doc["finished_at"] = _now()
        run_doc["duration_ms"] = int((_now() - start_time).total_seconds() * 1000)
        await _update_connection_status(db, conn_id, "error", str(e))

    finally:
        await release_sync_lock(db, tenant_id, hotel_id)

    # 9. Save run
    await db.sheet_sync_runs.update_one({"_id": run_id}, {"$set": run_doc})
    return run_doc


async def _update_connection_status(
    db, conn_id: str, status: str, error: Optional[str]
) -> None:
    await db.hotel_portfolio_sources.update_one(
        {"_id": conn_id},
        {"$set": {
            "last_sync_at": _now(),
            "last_sync_status": status,
            "last_error": error,
            "updated_at": _now(),
        }},
    )


# ── Scheduled Sync ────────────────────────────────────────

async def run_scheduled_portfolio_sync(
    db, max_concurrent: int = 3
) -> Dict[str, Any]:
    """Run sync for all enabled connections. Called by scheduler."""
    cursor = db.hotel_portfolio_sources.find({
        "sync_enabled": True,
        "source_type": "google_sheets",
    })

    total = 0
    success = 0
    failed = 0
    skipped = 0

    async for conn in cursor:
        total += 1
        try:
            result = await run_hotel_sheet_sync(db, conn, trigger="scheduled")
            status = result.get("status", "")
            if status in ("success", "no_change"):
                success += 1
            elif status == "skipped":
                skipped += 1
            else:
                failed += 1
        except Exception as e:
            logger.error("Scheduled sync error for hotel %s: %s", conn.get("hotel_id"), e)
            failed += 1

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "skipped": skipped,
    }


# ── Stale Detection ───────────────────────────────────────

async def get_stale_connections(
    db, tenant_id: str, stale_minutes: int = 30
) -> List[Dict[str, Any]]:
    """Get connections that haven't synced in > stale_minutes."""
    cutoff = _now() - timedelta(minutes=stale_minutes)
    cursor = db.hotel_portfolio_sources.find({
        "tenant_id": tenant_id,
        "sync_enabled": True,
        "$or": [
            {"last_sync_at": {"$lt": cutoff}},
            {"last_sync_at": None},
            {"last_sync_at": {"$exists": False}},
        ],
    })
    return await cursor.to_list(300)


async def get_portfolio_health(
    db, tenant_id: str
) -> Dict[str, Any]:
    """Get portfolio health summary."""
    pipeline = [
        {"$match": {"tenant_id": tenant_id}},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "enabled": {"$sum": {"$cond": [{"$eq": ["$sync_enabled", True]}, 1, 0]}},
            "healthy": {"$sum": {"$cond": [{"$eq": ["$last_sync_status", "success"]}, 1, 0]}},
            "no_change": {"$sum": {"$cond": [{"$eq": ["$last_sync_status", "no_change"]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [{"$eq": ["$last_sync_status", "error"]}, 1, 0]}},
            "not_configured": {"$sum": {"$cond": [{"$eq": ["$last_sync_status", "not_configured"]}, 1, 0]}},
        }},
    ]
    results = await db.hotel_portfolio_sources.aggregate(pipeline).to_list(1)
    if results:
        r = results[0]
        r.pop("_id", None)
        return r
    return {
        "total": 0,
        "enabled": 0,
        "healthy": 0,
        "no_change": 0,
        "failed": 0,
        "not_configured": 0,
    }
