"""Google Sheets Live Sync Service.

Handles: fetch → map → validate → fingerprint → delta → upsert.
Idempotent: unchanged rows are skipped via SHA256 fingerprinting.
Tenant-isolated: all operations scoped to organization_id.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.services.google_sheets_client import fetch_sheet_data, is_configured
from app.services.import_service import validate_hotels, get_existing_hotel_names

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Column Mapping ───────────────────────────────────────────

def apply_mapping(
    headers: List[str],
    rows: List[List[str]],
    column_mapping: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Apply column mapping (header_name -> field_name) to rows."""
    header_to_idx = {h: i for i, h in enumerate(headers)}
    result = []
    for row_num, row in enumerate(rows, start=2):
        record: Dict[str, Any] = {"_row_number": row_num}
        for header_name, field_name in column_mapping.items():
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


def make_row_key(sheet_id: str, worksheet: str, row_number: int) -> str:
    return f"{sheet_id}|{worksheet}|{row_number}"


# ── Delta Detection ───────────────────────────────────────

async def compute_delta(
    db,
    tenant_id: str,
    connection_id: str,
    sheet_id: str,
    worksheet: str,
    mapped_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Filter out rows that haven't changed since last sync."""
    changed = []
    for row in mapped_rows:
        row_num = row.get("_row_number", 0)
        row_key = make_row_key(sheet_id, worksheet, row_num)
        fp = fingerprint_row(row)

        existing = await db.sheet_row_fingerprints.find_one({
            "tenant_id": tenant_id,
            "sheet_connection_id": connection_id,
            "row_key": row_key,
        })

        if existing and existing.get("fingerprint") == fp:
            continue  # Unchanged

        # Upsert fingerprint
        await db.sheet_row_fingerprints.update_one(
            {
                "tenant_id": tenant_id,
                "sheet_connection_id": connection_id,
                "row_key": row_key,
            },
            {
                "$set": {"fingerprint": fp, "updated_at": _now()},
                "$setOnInsert": {"_id": str(uuid.uuid4())},
            },
            upsert=True,
        )
        changed.append(row)

    return changed


# ── Upsert Hotels ──────────────────────────────────────────

async def upsert_hotels_bulk(
    db,
    org_id: str,
    rows: List[Dict[str, Any]],
    source: str = "sheet_sync",
) -> Tuple[int, int, List[Dict[str, Any]]]:
    """Upsert hotels by (organization_id, name, city).

    Returns (upsert_count, error_count, errors).
    """
    now = _now()
    upserts = 0
    errors_list: List[Dict[str, Any]] = []

    for row in rows:
        row_num = row.pop("_row_number", 0)
        name = (row.get("name") or "").strip()
        city = (row.get("city") or "").strip()
        if not name or not city:
            errors_list.append({"row_number": row_num, "field": "name/city", "message": "Eksik"})
            continue

        try:
            update_fields: Dict[str, Any] = {
                "updated_at": now,
                "updated_by": source,
            }
            if row.get("country"):
                update_fields["country"] = row["country"].strip()
            if row.get("description"):
                update_fields["description"] = row["description"].strip()
            if row.get("image_url"):
                update_fields["image_url"] = row["image_url"].strip()
            if row.get("address"):
                update_fields["address"] = row["address"].strip()
            if row.get("phone"):
                update_fields["phone"] = row["phone"].strip()
            if row.get("email"):
                update_fields["email"] = row["email"].strip()
            if row.get("price"):
                try:
                    update_fields["base_price"] = float(str(row["price"]).replace(",", "."))
                except (ValueError, TypeError):
                    pass
            if row.get("stars"):
                try:
                    update_fields["stars"] = int(str(row["stars"]))
                except (ValueError, TypeError):
                    pass

            await db.hotels.update_one(
                {"organization_id": org_id, "name": name, "city": city},
                {
                    "$set": update_fields,
                    "$setOnInsert": {
                        "_id": str(uuid.uuid4()),
                        "organization_id": org_id,
                        "name": name,
                        "city": city,
                        "active": True,
                        "created_at": now,
                        "created_by": source,
                    },
                },
                upsert=True,
            )
            upserts += 1
        except Exception as e:
            errors_list.append({"row_number": row_num, "field": "general", "message": str(e)})

    return upserts, len(errors_list), errors_list


# ── Full Sync Run ─────────────────────────────────────────

async def acquire_sync_lock(db, tenant_id: str, ttl_minutes: int = 10) -> bool:
    """Try to acquire a sync lock. Returns True if acquired."""
    now = _now()
    from datetime import timedelta
    expiry = now - timedelta(minutes=ttl_minutes)

    # Try to claim lock (only if not exists or expired)
    result = await db.sheet_sync_locks.update_one(
        {
            "tenant_id": tenant_id,
            "$or": [
                {"locked_at": {"$lt": expiry}},
                {"locked_at": {"$exists": False}},
            ],
        },
        {
            "$set": {"locked_at": now},
            "$setOnInsert": {"_id": str(uuid.uuid4()), "tenant_id": tenant_id},
        },
        upsert=True,
    )
    return result.modified_count > 0 or result.upserted_id is not None


async def release_sync_lock(db, tenant_id: str) -> None:
    await db.sheet_sync_locks.delete_one({"tenant_id": tenant_id})


async def run_sheet_sync(
    db,
    connection: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a full sync cycle for a sheet connection.

    Returns sync run summary.
    """
    conn_id = connection["_id"]
    tenant_id = connection["tenant_id"]
    org_id = connection["organization_id"]
    sheet_id = connection["sheet_id"]
    worksheet = connection.get("worksheet_name", "Sheet1")
    col_mapping = connection.get("column_mapping", {})

    run_id = str(uuid.uuid4())
    run_doc = {
        "_id": run_id,
        "tenant_id": tenant_id,
        "sheet_connection_id": conn_id,
        "run_id": run_id,
        "started_at": _now(),
        "finished_at": None,
        "status": "running",
        "rows_fetched": 0,
        "rows_processed": 0,
        "upserts": 0,
        "errors": 0,
        "error_message": None,
    }
    await db.sheet_sync_runs.insert_one(run_doc)

    try:
        # 1. Fetch
        headers, rows = fetch_sheet_data(sheet_id, worksheet)
        run_doc["rows_fetched"] = len(rows)

        # 2. Map
        if not col_mapping:
            raise RuntimeError("Sütun eşleştirmesi yapılmamış.")
        mapped = apply_mapping(headers, rows, col_mapping)

        # 3. Validate
        existing_names = await get_existing_hotel_names(db, org_id)
        # For upsert mode, don't treat existing names as duplicates
        valid, val_errors = validate_hotels(mapped, set())
        run_doc["rows_processed"] = len(valid)

        # 4. Delta
        changed = await compute_delta(db, tenant_id, conn_id, sheet_id, worksheet, valid)

        # 5. Upsert
        if changed:
            upsert_count, err_count, upsert_errors = await upsert_hotels_bulk(db, org_id, changed)
            run_doc["upserts"] = upsert_count
            run_doc["errors"] = err_count + len(val_errors)
        else:
            run_doc["upserts"] = 0
            run_doc["errors"] = len(val_errors)

        run_doc["status"] = "ok"
        run_doc["finished_at"] = _now()

        # Update connection
        await db.sheet_connections.update_one(
            {"_id": conn_id},
            {"$set": {
                "last_sync_at": _now(),
                "last_sync_status": "ok",
                "last_sync_error": None,
                "stats": {
                    "last_rows": len(rows),
                    "last_upserts": run_doc["upserts"],
                    "last_errors": run_doc["errors"],
                },
                "updated_at": _now(),
            }},
        )

    except Exception as e:
        logger.error("Sheet sync failed for connection %s: %s", conn_id, e)
        run_doc["status"] = "error"
        run_doc["error_message"] = str(e)
        run_doc["finished_at"] = _now()

        await db.sheet_connections.update_one(
            {"_id": conn_id},
            {"$set": {
                "last_sync_at": _now(),
                "last_sync_status": "error",
                "last_sync_error": str(e),
                "updated_at": _now(),
            }},
        )

    # Save run
    await db.sheet_sync_runs.update_one(
        {"_id": run_id},
        {"$set": run_doc},
    )

    return run_doc


async def run_scheduled_sync(db) -> int:
    """Run sync for all enabled connections. Called by scheduler."""
    cursor = db.sheet_connections.find({"sync_enabled": True})
    synced = 0
    async for conn in cursor:
        tenant_id = conn.get("tenant_id", "")
        if not await acquire_sync_lock(db, tenant_id):
            logger.info("Skipping sync for tenant %s (locked)", tenant_id)
            continue
        try:
            await run_sheet_sync(db, conn)
            synced += 1
        except Exception as e:
            logger.error("Scheduled sync error for tenant %s: %s", tenant_id, e)
        finally:
            await release_sync_lock(db, tenant_id)
    return synced
