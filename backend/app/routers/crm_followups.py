from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth import get_current_user, require_roles
from app.db import get_db

router = APIRouter(prefix="/api/crm", tags=["crm"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_due_until(due_until: Optional[str]) -> date:
    if not due_until:
        return _utc_now().date()
    try:
        # expects YYYY-MM-DD
        return date.fromisoformat(due_until)
    except Exception:
        raise HTTPException(status_code=422, detail="INVALID_DUE_UNTIL_DATE")


def _safe_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_date(value: Any) -> Optional[date]:
    """Accept datetime|date|iso-string and return date."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).date()
    if isinstance(value, str):
        # best-effort: YYYY-MM-DD or full ISO
        try:
            if len(value) == 10:
                return date.fromisoformat(value)
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).date()
        except Exception:
            return None
    return None


async def _get_linked_hotels(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    agency_id: str,
) -> List[str]:
    cur = db.agency_hotel_links.find(
        {"organization_id": organization_id, "agency_id": agency_id, "active": True},
        {"hotel_id": 1},
    )
    hotel_ids: List[str] = []
    async for doc in cur:
        hid = doc.get("hotel_id")
        if hid is not None:
            hotel_ids.append(str(hid))
    return hotel_ids


async def _fetch_hotels_map(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    hotel_ids: List[str],
    q: Optional[str],
) -> Dict[str, Dict[str, Any]]:
    """Fetch hotel documents used for display + filtering by q."""
    if not hotel_ids:
        return {}

    base_filter: Dict[str, Any] = {"organization_id": organization_id, "_id": {"$in": hotel_ids}}
    proj = {"name": 1, "title": 1, "city": 1, "phone": 1, "email": 1}

    # NOTE: If your hotels _id is ObjectId in DB, "_id": {"$in": hotel_ids} won't match.
    # In that case, convert to ObjectId list here. (We keep it string because your flows often store ids as strings.)
    cur = db.hotels.find(base_filter, proj)

    items: Dict[str, Dict[str, Any]] = {}
    q_norm = (q or "").strip().lower()
    async for h in cur:
        hid = str(h.get("_id"))
        name = (h.get("name") or h.get("title") or "").strip()
        city = (h.get("city") or "").strip()
        phone = (h.get("phone") or "").strip()
        email = (h.get("email") or "").strip()

        if q_norm:
            hay = f"{name} {city} {phone} {email}".lower()
            if q_norm not in hay:
                continue

        items[hid] = {
            "hotel_id": hid,
            "hotel_name": name or hid,
            "city": city or None,
            "phone": phone or None,
            "email": email or None,
        }

    return items


async def _fetch_primary_contacts_map(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    hotel_ids: List[str],
) -> Dict[str, Dict[str, Any]]:
    if not hotel_ids:
        return {}

    cur = db.hotel_contacts.find(
        {
            "organization_id": organization_id,
            "hotel_id": {"$in": hotel_ids},
            "is_primary": True,
            "is_active": {"$ne": False},
        },
        {"hotel_id": 1, "full_name": 1, "first_name": 1, "last_name": 1, "phone": 1, "whatsapp": 1, "email": 1},
    )

    out: Dict[str, Dict[str, Any]] = {}
    async for c in cur:
        hid = str(c.get("hotel_id"))
        name = (c.get("full_name") or "").strip()
        if not name:
            fn = (c.get("first_name") or "").strip()
            ln = (c.get("last_name") or "").strip()
            name = (f"{fn} {ln}").strip()

        out[hid] = {
            "name": name or None,
            "phone": (c.get("phone") or None),
            "whatsapp": (c.get("whatsapp") or None),
            "email": (c.get("email") or None),
        }
    return out


async def _fetch_last_note_map(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    agency_id: str,
    hotel_ids: List[str],
) -> Dict[str, Dict[str, Any]]:
    """Return last note/call per hotel for this agency."""
    if not hotel_ids:
        return {}

    pipeline = [
        {"$match": {"organization_id": organization_id, "agency_id": agency_id, "hotel_id": {"$in": hotel_ids}}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$hotel_id", "doc": {"$first": "$$ROOT"}}},
    ]
    cur = db.hotel_crm_notes.aggregate(pipeline)

    out: Dict[str, Dict[str, Any]] = {}
    async for row in cur:
        doc = row.get("doc") or {}
        hid = str(row.get("_id"))
        created_at = doc.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except Exception:
                created_at = None

        out[hid] = {
            "created_at": created_at,
            "type": doc.get("type") or "note",
            "subject": doc.get("subject") or "",
            "call_outcome": doc.get("call_outcome"),
        }
    return out


async def _fetch_callback_map(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    agency_id: str,
    hotel_ids: List[str],
    lookback_days: int = 30,
) -> Dict[str, Dict[str, Any]]:
    """Return most recent callback call note per hotel (if any) within lookback."""
    if not hotel_ids:
        return {}

    since = _utc_now() - timedelta(days=lookback_days)
    pipeline = [
        {
            "$match": {
                "organization_id": organization_id,
                "agency_id": agency_id,
                "hotel_id": {"$in": hotel_ids},
                "type": "call",
                "call_outcome": "callback",
                "created_at": {"$gte": since},
            }
        },
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$hotel_id", "doc": {"$first": "$$ROOT"}}},
    ]
    cur = db.hotel_crm_notes.aggregate(pipeline)

    out: Dict[str, Dict[str, Any]] = {}
    async for row in cur:
        doc = row.get("doc") or {}
        hid = str(row.get("_id"))
        out[hid] = {"created_at": doc.get("created_at"), "subject": doc.get("subject") or ""}
    return out


async def _fetch_tasks_agg_map(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    agency_id: str,
    hotel_ids: List[str],
    due_until: date,
) -> Dict[str, Dict[str, Any]]:
    """Aggregate open tasks metrics per hotel."""
    if not hotel_ids:
        return {}

    # Fetch open tasks; we'll compute date comparisons in Python to avoid schema variance (date vs datetime vs string).
    cur = db.hotel_crm_tasks.find(
        {"organization_id": organization_id, "agency_id": agency_id, "hotel_id": {"$in": hotel_ids}, "status": "open"},
        {"_id": 1, "hotel_id": 1, "due_date": 1, "updated_at": 1, "assignee_user_id": 1, "title": 1},
    )

    out: Dict[str, Dict[str, Any]] = {}
    async for t in cur:
        hid = str(t.get("hotel_id"))
        rec = out.setdefault(
            hid,
            {
                "open_tasks": 0,
                "due_today": 0,
                "overdue": 0,
                "next_due_date": None,
                "next_task_id": None,
                "next_task_title": None,
                "next_task_updated_at": None,
                "last_task_update_at": None,
            },
        )
        rec["open_tasks"] += 1

        due_d = _to_date(t.get("due_date"))
        if due_d:
            if due_d == due_until:
                rec["due_today"] += 1
            elif due_d < due_until:
                rec["overdue"] += 1

            nd = rec.get("next_due_date")
            upd_for_task = t.get("updated_at")
            if isinstance(upd_for_task, str):
                try:
                    upd_for_task = datetime.fromisoformat(upd_for_task.replace("Z", "+00:00"))
                except Exception:
                    upd_for_task = None
            if isinstance(upd_for_task, datetime) and upd_for_task.tzinfo is None:
                upd_for_task = upd_for_task.replace(tzinfo=timezone.utc)

            better_candidate = False
            if nd is None or due_d < nd:
                better_candidate = True
            elif nd == due_d and isinstance(upd_for_task, datetime):
                existing_upd = rec.get("next_task_updated_at")
                if not isinstance(existing_upd, datetime) or upd_for_task > existing_upd:
                    better_candidate = True

            if better_candidate:
                rec["next_due_date"] = due_d
                rec["next_task_id"] = str(t.get("_id")) if t.get("_id") is not None else None
                rec["next_task_title"] = (t.get("title") or "").strip() or None
                rec["next_task_updated_at"] = upd_for_task

        upd = t.get("updated_at")
        if isinstance(upd, str):
            try:
                upd = datetime.fromisoformat(upd.replace("Z", "+00:00"))
            except Exception:
                upd = None
        if isinstance(upd, datetime):
            if upd.tzinfo is None:
                upd = upd.replace(tzinfo=timezone.utc)
            last = rec.get("last_task_update_at")
            if last is None or upd > last:
                rec["last_task_update_at"] = upd

    return out


def _priority_key(item: Dict[str, Any]) -> Tuple[int, int, int, int]:
    """Sort: callback -> overdue -> due_today -> idle_days desc"""
    s = item.get("signals") or {}
    callback = 1 if (item.get("_flags") or {}).get("callback") else 0
    overdue = int(s.get("overdue") or 0)
    due_today = int(s.get("due_today") or 0)
    idle = int(s.get("idle_days") or 0)
    return (callback, overdue, due_today, idle)


@router.get(
    "/follow-ups",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "hotel_admin", "hotel_staff", "super_admin"]))],
)
async def get_followups(
    days_idle: int = Query(7, ge=1, le=365),
    due_until: Optional[str] = Query(None),
    scope: str = Query("agency"),
    hotel_id: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    # v1.1: agency only
    scope = (scope or "agency").strip().lower()
    if scope != "agency":
        raise HTTPException(status_code=422, detail="SCOPE_NOT_SUPPORTED")

    roles = set(user.get("roles") or [])
    # Explicitly forbid hotel roles for v1.1
    if roles.intersection({"hotel_admin", "hotel_staff"}):
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    organization_id = str(user.get("organization_id"))
    agency_id = str(user.get("agency_id") or "")
    if not agency_id:
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    due_until_d = _parse_due_until(due_until)

    linked_hotel_ids = await _get_linked_hotels(db, organization_id, agency_id)
    if not linked_hotel_ids:
        return {"items": [], "next_cursor": None, "meta": {"days_idle": days_idle, "due_until": str(due_until_d), "count": 0}}

    # Optional hotel_id filter: must still be linked
    if hotel_id:
        if str(hotel_id) not in set(linked_hotel_ids):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
        linked_hotel_ids = [str(hotel_id)]

    # Basic pagination (cursor = hotel_id offset). Keep it simple for v1.1.
    hotel_ids_page = linked_hotel_ids
    if cursor:
        try:
            idx = hotel_ids_page.index(cursor)
            hotel_ids_page = hotel_ids_page[idx + 1 :]
        except ValueError:
            pass
    hotel_ids_page = hotel_ids_page[:limit]
    next_cursor = hotel_ids_page[-1] if len(hotel_ids_page) == limit else None

    hotels_map = await _fetch_hotels_map(db, organization_id, hotel_ids_page, q)
    # Apply q filtering effect: hotels_map only contains matches
    hotel_ids_filtered = list(hotels_map.keys())
    if not hotel_ids_filtered:
        return {"items": [], "next_cursor": None, "meta": {"days_idle": days_idle, "due_until": str(due_until_d), "count": 0}}

    primary_map = await _fetch_primary_contacts_map(db, organization_id, hotel_ids_filtered)
    last_note_map = await _fetch_last_note_map(db, organization_id, agency_id, hotel_ids_filtered)
    callback_map = await _fetch_callback_map(db, organization_id, agency_id, hotel_ids_filtered, lookback_days=30)
    tasks_map = await _fetch_tasks_agg_map(db, organization_id, agency_id, hotel_ids_filtered, due_until_d)

    now = _utc_now()

    items: List[Dict[str, Any]] = []
    for hid in hotel_ids_filtered:
        hinfo = hotels_map.get(hid) or {"hotel_id": hid, "hotel_name": hid}

        last_note = last_note_map.get(hid)
        tasks_agg = tasks_map.get(hid) or {}
        last_task_update_at = tasks_agg.get("last_task_update_at")

        note_dt = (last_note or {}).get("created_at")
        if isinstance(note_dt, str):
            try:
                note_dt = datetime.fromisoformat(note_dt.replace("Z", "+00:00"))
            except Exception:
                note_dt = None
        if isinstance(note_dt, datetime) and note_dt.tzinfo is None:
            note_dt = note_dt.replace(tzinfo=timezone.utc)

        if isinstance(last_task_update_at, datetime) and last_task_update_at.tzinfo is None:
            last_task_update_at = last_task_update_at.replace(tzinfo=timezone.utc)

        # last_touch = max(note_dt, last_task_update_at)
        last_touch_at: Optional[datetime] = None
        last_touch_type: str = "none"
        last_touch_summary: str = ""

        if note_dt and last_task_update_at:
            if note_dt >= last_task_update_at:
                last_touch_at = note_dt
                last_touch_type = last_note.get("type") or "note"
                last_touch_summary = (last_note.get("subject") or "")[:140]
            else:
                last_touch_at = last_task_update_at
                last_touch_type = "task_update"
                last_touch_summary = "Görev güncellendi"
        elif note_dt:
            last_touch_at = note_dt
            last_touch_type = last_note.get("type") or "note"
            last_touch_summary = (last_note.get("subject") or "")[:140]
        elif last_task_update_at:
            last_touch_at = last_task_update_at
            last_touch_type = "task_update"
            last_touch_summary = "Görev güncellendi"

        idle_days = 9999
        if last_touch_at:
            idle_days = max(0, int((now - last_touch_at).total_seconds() // 86400))

        open_tasks = int(tasks_agg.get("open_tasks") or 0)
        due_today = int(tasks_agg.get("due_today") or 0)
        overdue = int(tasks_agg.get("overdue") or 0)
        next_due_date = tasks_agg.get("next_due_date")
        next_task_id = tasks_agg.get("next_task_id")
        next_task_title = tasks_agg.get("next_task_title")

        callback_hit = hid in callback_map

        # suggested action
        reason = "idle" if idle_days >= days_idle else "review"
        action_type = "call"
        if callback_hit:
            reason = "callback"
            action_type = "call"
        elif overdue > 0:
            reason = "overdue"
            action_type = "call"
        elif due_today > 0:
            reason = "due_today"
            action_type = "call"
        elif idle_days >= days_idle:
            reason = "idle"
            action_type = "call"

        item = {
            "hotel_id": hid,
            "hotel_name": hinfo.get("hotel_name"),
            "city": hinfo.get("city"),
            "phone": hinfo.get("phone"),
            "primary_contact": primary_map.get(hid),
            "signals": {
                "idle_days": idle_days if last_touch_at else None,
                "last_touch_at": _safe_iso(last_touch_at),
                "last_touch_type": last_touch_type,
                "last_touch_summary": last_touch_summary,
                "open_tasks": open_tasks,
                "due_today": due_today,
                "overdue": overdue,
                "next_due_date": (next_due_date.isoformat() if isinstance(next_due_date, date) else None),
                "next_task_id": next_task_id,
                "next_task_title": next_task_title,
            },
            "suggested_action": {"type": action_type, "reason": reason},
            "_flags": {"callback": callback_hit},
        }
        items.append(item)

    # sort: callback -> overdue -> due_today -> idle_days desc
    items.sort(key=_priority_key, reverse=True)

    # drop internal flags
    for it in items:
        it.pop("_flags", None)

    return {
        "items": items,
        "next_cursor": next_cursor,
        "meta": {"days_idle": days_idle, "due_until": str(due_until_d), "count": len(items)},
    }
