from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase as Database


def _normalize_for_json(obj: Any) -> Any:
    """Recursively normalize values for JSON/Pydantic serialization.

    - ObjectId -> str
    - datetime -> isoformat() string
    - dict/list -> walk recursively
    """
    if isinstance(obj, dict):
        return {k: _normalize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_for_json(v) for v in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def _normalize_contacts(contacts: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not contacts:
        return []
    normalized: List[Dict[str, Any]] = []
    primary_seen = False
    for raw in contacts:
        c = dict(raw)
        ctype = c.get("type")
        if ctype not in {"phone", "email"}:
            continue
        # Trim and normalize value by type
        value = str(c.get("value", "")).strip()
        if not value:
            continue
        if ctype == "email":
            value = value.lower()
        if ctype == "phone":
            value = _normalize_phone(value)
            if not value:
                continue
        c["value"] = value
        c["type"] = ctype
        # Only one primary
        if c.get("is_primary") and not primary_seen:
            primary_seen = True
            c["is_primary"] = True
        else:
            c["is_primary"] = False
        normalized.append(c)
    return normalized


def _normalize_tags(tags: Optional[List[str]]) -> List[str]:
    if not tags:
        return []
    seen = set()
    result: List[str] = []
    for raw in tags:
        if raw is None:
            continue
        t = str(raw).strip().lower()
        if not t:
            continue
        if t in seen:
            continue
        seen.add(t)
        result.append(t)
    return result


async def create_customer(db: Database, organization_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    customer_id = f"cust_{uuid4().hex}"

    tags = _normalize_tags(data.get("tags"))
    contacts = _normalize_contacts(data.get("contacts"))

    doc = {
        "id": customer_id,
        "organization_id": organization_id,
        "type": data.get("type", "individual"),
        "name": data["name"],
        "tc_vkn": data.get("tc_vkn"),
        "tags": tags,
        "contacts": contacts,
        "assigned_user_id": data.get("assigned_user_id"),
        "created_at": now,
        "updated_at": now,
    }
    await db.customers.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def list_customers(
    db: Database,
    organization_id: str,
    *,
    search: Optional[str] = None,
    cust_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Dict[str, Any]], int]:
    q: Dict[str, Any] = {"organization_id": organization_id}

    if cust_type:
        q["type"] = cust_type

    if tags:
        q["tags"] = {"$in": tags}

    if search:
        s = search.strip()
        q["$or"] = [
            {"name": {"$regex": s, "$options": "i"}},
            {"contacts.value": {"$regex": s, "$options": "i"}},
        ]

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 25
    if page_size > 100:
        page_size = 100

    skip = (page - 1) * page_size

    total = await db.customers.count_documents(q)
    cursor = (
        db.customers.find(q, {"_id": 0})
        .sort([("updated_at", -1)])
        .skip(skip)
        .limit(page_size)
    )
    items = await cursor.to_list(length=page_size)
    return items, total


async def get_customer(db: Database, organization_id: str, customer_id: str) -> Optional[Dict[str, Any]]:
    doc = await db.customers.find_one({"organization_id": organization_id, "id": customer_id}, {"_id": 0})
    return doc


def _normalize_phone(value: str) -> str:
  digits = [ch for ch in str(value) if ch.isdigit()]
  return "".join(digits)


async def find_or_create_customer_for_booking(
    db: Database,
    organization_id: str,
    *,
    booking: Dict[str, Any],
    created_by_user_id: Optional[str] = None,
) -> Optional[str]:
    # Try both 'customer' (B2B bookings) and 'guest' (other bookings) fields
    customer_data = booking.get("customer") or booking.get("guest") or {}
    email_raw = (customer_data.get("email") or "").strip().lower()
    phone_raw = (customer_data.get("phone") or "").strip()
    phone_norm = _normalize_phone(phone_raw) if phone_raw else ""

    if not email_raw and not phone_norm:
        return None

    # 1) Try match by email (deterministic, most recently updated)
    from pymongo import DESCENDING
    from pymongo.errors import DuplicateKeyError

    if email_raw:
        cursor = (
            db.customers.find(
                {
                    "organization_id": organization_id,
                    "contacts": {
                        "$elemMatch": {
                            "type": "email",
                            "value": email_raw,
                        }
                    },
                },
                {"_id": 0},
            )
            .sort([("updated_at", DESCENDING)])
            .limit(1)
        )
        items = await cursor.to_list(length=1)
        if items:
            return items[0].get("id")

    # 2) Try match by phone (deterministic)
    if phone_norm:
        cursor = (
            db.customers.find(
                {
                    "organization_id": organization_id,
                    "contacts": {
                        "$elemMatch": {
                            "type": "phone",
                            "value": phone_norm,
                        }
                    },
                },
                {"_id": 0},
            )
            .sort([("updated_at", DESCENDING)])
            .limit(1)
        )
        items = await cursor.to_list(length=1)
        if items:
            return items[0].get("id")

    # 3) Create new customer (duplicate-safe with retry)
    name = (customer_data.get("name") or customer_data.get("full_name") or "Misafir").strip() or "Misafir"
    contacts: List[Dict[str, Any]] = []
    if email_raw:
        contacts.append({"type": "email", "value": email_raw, "is_primary": True})
    if phone_norm:
        contacts.append({"type": "phone", "value": phone_norm, "is_primary": not contacts})

    data = {
        "type": "individual",
        "name": name,
        "contacts": contacts,
    }
    try:
        created = await create_customer(db, organization_id, created_by_user_id or "system", data)
        return created.get("id")
    except DuplicateKeyError:
        # Another process created a customer with this contact concurrently.
        # Retry by looking up by normalized email/phone.
        q: Dict[str, Any] = {"organization_id": organization_id}
        contact_match: Dict[str, Any] = {}
        if email_raw:
            contact_match = {"type": "email", "value": email_raw}
        elif phone_norm:
            contact_match = {"type": "phone", "value": phone_norm}
        if contact_match:
            q["contacts"] = {"$elemMatch": contact_match}
            existing = await db.customers.find_one(q, {"_id": 0})
            if existing:
                return existing.get("id")
        return None


async def patch_customer(
    db: Database,
    organization_id: str,
    customer_id: str,
    patch: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    update = {k: v for k, v in patch.items() if v is not None}

    if "tags" in update:
        update["tags"] = _normalize_tags(update.get("tags"))
    if "contacts" in update:
        update["contacts"] = _normalize_contacts(update.get("contacts"))

    if not update:
        return await get_customer(db, organization_id, customer_id)

    update["updated_at"] = datetime.utcnow()

    res = await db.customers.find_one_and_update(
        {"organization_id": organization_id, "id": customer_id},
        {"$set": update},
        projection={"_id": 0},
        return_document=True,
    )
    return res


async def get_customer_detail(
    db: Database,
    organization_id: str,
    customer_id: str,
) -> Optional[Dict[str, Any]]:
    customer = await get_customer(db, organization_id, customer_id)
    if not customer:
        return None

    recent_bookings: list[dict] = []

    # When bookings.customer_id is present, load recent bookings for this customer.
    # Sort by created_at desc; if created_at is missing, fall back to updated_at.
    booking_sort_field = "created_at"
    sample_booking = await db.bookings.find_one(
        {"organization_id": organization_id, "customer_id": customer_id},
        {"created_at": 1, "updated_at": 1},
    )
    if sample_booking and not sample_booking.get("created_at") and sample_booking.get("updated_at"):
        booking_sort_field = "updated_at"


async def find_duplicate_customers(db: Database, organization_id: str) -> List[Dict[str, Any]]:
    """Find duplicate customers for an organization based on contacts (email/phone).

    Dry-run only: does NOT modify any data. Intended for admin tooling & reporting.
    """
    pipeline = [
        {"$match": {"organization_id": organization_id, "contacts": {"$exists": True, "$ne": []}}},
        {"$unwind": "$contacts"},
        {"$match": {"contacts.type": {"$in": ["email", "phone"]}, "contacts.value": {"$ne": None}}},
        {
            "$group": {
                "_id": {
                    "type": "$contacts.type",
                    "value": "$contacts.value",
                },
                "customers": {
                    "$push": {
                        "id": "$id",
                        "name": "$name",
                        "created_at": "$created_at",
                        "updated_at": "$updated_at",
                    }
                },
            }
        },
        {"$match": {"customers.1": {"$exists": True}}},  # only groups with at least 2 customers
    ]

    cursor = db.customers.aggregate(pipeline)
    raw_groups = await cursor.to_list(length=1000)

    clusters: List[Dict[str, Any]] = []
    for grp in raw_groups:
        contact_type = grp["_id"]["type"]
        contact_value = grp["_id"]["value"]
        customers = grp["customers"] or []

        # deterministically sort: updated_at desc, created_at desc, id asc
        def _sort_key(c: Dict[str, Any]):
            return (
                c.get("updated_at") or datetime.min,
                c.get("created_at") or datetime.min,
                c.get("id") or "",
            )

        customers_sorted = sorted(customers, key=_sort_key, reverse=True)
        primary = customers_sorted[0]
        duplicates = customers_sorted[1:]

        clusters.append(
            {
                "organization_id": organization_id,
                "contact": {"type": contact_type, "value": contact_value},
                "primary": primary,
                "duplicates": duplicates,
            }
        )

    return clusters


async def perform_customer_merge(
    db: Database,
    organization_id: str,
    primary_id: str,
    duplicate_ids: List[str],
    *,
    dry_run: bool,
    merged_by_user_id: str,
) -> Dict[str, Any]:
    """Merge customers by rewiring references and soft-merging duplicates.

    - dry_run=True: only counts, no writes
    - dry_run=False: perform rewires + soft-merge
    """
    from pymongo import UpdateMany
    from pymongo.errors import DuplicateKeyError

    primary_id = (primary_id or "").strip()
    if not primary_id:
        raise ValueError("primary_id is required")

    # Normalize duplicate_ids: strip, remove blanks, remove primary, dedupe
    dup_ids_clean: List[str] = []
    for raw in duplicate_ids or []:
        v = (raw or "").strip()
        if not v or v == primary_id:
            continue
        dup_ids_clean.append(v)
    dup_set = set(dup_ids_clean)

    if not dup_set:
        return {
            "organization_id": organization_id,
            "primary_id": primary_id,
            "merged_ids": [],
            "skipped_ids": [],
            "rewired": {
                "bookings": {"matched": 0, "modified": 0},
                "deals": {"matched": 0, "modified": 0},
                "tasks": {"matched": 0, "modified": 0},
                "activities": {"matched": 0, "modified": 0},
            },
            "dry_run": dry_run,
        }

    # Validate primary exists
    primary = await db.customers.find_one(
        {"organization_id": organization_id, "id": primary_id},
        {"_id": 0, "id": 1},
    )
    if not primary:
        raise ValueError("primary_customer_not_found")

    # Load duplicates and detect conflicts / already merged
    duplicates = await db.customers.find(
        {"organization_id": organization_id, "id": {"$in": list(dup_set)}},
        {"_id": 0, "id": 1, "is_merged": 1, "merged_into": 1},
    ).to_list(length=len(dup_set))

    found_ids = {d["id"] for d in duplicates}
    skipped_ids: List[str] = []

    # Any ids not found -> skip
    for did in dup_set:
        if did not in found_ids:
            skipped_ids.append(did)

    effective_dup_ids: List[str] = []
    for doc in duplicates:
        did = doc["id"]
        if doc.get("is_merged"):
            merged_into = doc.get("merged_into")
            if merged_into == primary_id:
                # already merged into this primary -> idempotent skip
                skipped_ids.append(did)
                continue
            # merged into different customer -> conflict
            raise ValueError("customer_merge_conflict")
        effective_dup_ids.append(did)

    if not effective_dup_ids:
        return {
            "organization_id": organization_id,
            "primary_id": primary_id,
            "merged_ids": [],
            "skipped_ids": skipped_ids,
            "rewired": {
                "bookings": {"matched": 0, "modified": 0},
                "deals": {"matched": 0, "modified": 0},
                "tasks": {"matched": 0, "modified": 0},
                "activities": {"matched": 0, "modified": 0},
            },
            "dry_run": dry_run,
        }

    dup_set_eff = set(effective_dup_ids)

    rewired_counts = {
        "bookings": {"matched": 0, "modified": 0},
        "deals": {"matched": 0, "modified": 0},
        "tasks": {"matched": 0, "modified": 0},
        "activities": {"matched": 0, "modified": 0},
    }

    now = datetime.utcnow()

    # 1) bookings.customer_id
    bookings_filter = {
        "organization_id": organization_id,
        "customer_id": {"$in": list(dup_set_eff)},
    }
    rewired_counts["bookings"]["matched"] = await db.bookings.count_documents(bookings_filter)
    if not dry_run:
        res = await db.bookings.update_many(
            bookings_filter,
            {"$set": {"customer_id": primary_id, "updated_at": now}},
        )
        rewired_counts["bookings"]["modified"] = res.modified_count

    # 2) crm_deals.customer_id
    deals_filter = {
        "organization_id": organization_id,
        "customer_id": {"$in": list(dup_set_eff)},
    }
    rewired_counts["deals"]["matched"] = await db.crm_deals.count_documents(deals_filter)
    if not dry_run:
        res = await db.crm_deals.update_many(
            deals_filter,
            {"$set": {"customer_id": primary_id, "updated_at": now}},
        )
        rewired_counts["deals"]["modified"] = res.modified_count

    # 3) crm_tasks related customer
    tasks_filter = {
        "organization_id": organization_id,
        "related_type": "customer",
        "related_id": {"$in": list(dup_set_eff)},
    }
    rewired_counts["tasks"]["matched"] = await db.crm_tasks.count_documents(tasks_filter)
    if not dry_run:
        res = await db.crm_tasks.update_many(
            tasks_filter,
            {"$set": {"related_id": primary_id, "updated_at": now}},
        )
        rewired_counts["tasks"]["modified"] = res.modified_count

    # 4) crm_activities related customer
    acts_filter = {
        "organization_id": organization_id,
        "related_type": "customer",
        "related_id": {"$in": list(dup_set_eff)},
    }
    rewired_counts["activities"]["matched"] = await db.crm_activities.count_documents(acts_filter)
    if not dry_run:
        res = await db.crm_activities.update_many(
            acts_filter,
            {"$set": {"related_id": primary_id}},
        )
        rewired_counts["activities"]["modified"] = res.modified_count

    # Soft-merge duplicate customers
    if not dry_run:
        soft_fields: Dict[str, Any] = {
            "is_merged": True,
            "merged_into": primary_id,
            "merged_at": now,
            "merged_by": merged_by_user_id,
        }
        await db.customers.update_many(
            {
                "organization_id": organization_id,
                "id": {"$in": list(dup_set_eff)},
                "id": {"$ne": primary_id},
            },
            {"$set": soft_fields},
        )
        # Touch primary updated_at for recency
        await db.customers.update_one(
            {"organization_id": organization_id, "id": primary_id},
            {"$set": {"updated_at": now}},
        )

    return {
        "organization_id": organization_id,
        "primary_id": primary_id,
        "merged_ids": list(dup_set_eff) if not dry_run else [],
        "skipped_ids": skipped_ids,
        "rewired": rewired_counts,
        "dry_run": dry_run,
    }



    cursor = (
        db.bookings.find(
            {"organization_id": organization_id, "customer_id": customer_id},
            {"_id": 0},
        )
        .sort([(booking_sort_field, -1)])
        .limit(5)
    )
    recent_bookings = await cursor.to_list(length=5)

    open_deals = await db.crm_deals.find(
        {
            "organization_id": organization_id,
            "customer_id": customer_id,
            "status": "open",
        },
        {"_id": 0},
    ).sort([("updated_at", -1)]).limit(10).to_list(length=10)

    open_tasks = await db.crm_tasks.find(
        {
            "organization_id": organization_id,
            "related_type": "customer",
            "related_id": customer_id,
            "status": "open",
        },
        {"_id": 0},
    ).sort([("due_date", 1), ("updated_at", -1)]).limit(10).to_list(length=10)

    return _normalize_for_json(
        {
            "customer": customer,
            "recent_bookings": recent_bookings,
            "open_deals": open_deals,
            "open_tasks": open_tasks,
        }
    )
