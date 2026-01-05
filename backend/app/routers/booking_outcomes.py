from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.booking_outcomes import OPERATIONAL_REASONS, resolve_outcome_for_booking, upsert_booking_outcome
from app.utils import now_utc

router = APIRouter(prefix="/api/admin/booking-outcomes", tags=["admin-booking-outcomes"])


class BookingOutcomeItem(BaseModel):
  organization_id: str
  booking_id: str
  agency_id: str
  hotel_id: str
  booked_at: str | None = None
  checkin_date: str | None = None
  final_outcome: str
  outcome_source: str
  inferred_reason: str | None = None
  verified: bool
  verified_at: str | None = None
  created_at: str | None = None
  updated_at: str | None = None


class BookingOutcomeListResponse(BaseModel):
  ok: bool = True
  items: list[BookingOutcomeItem]


class BookingOutcomeRecomputeResponse(BaseModel):
  ok: bool = True
  dry_run: bool
  scanned: int
  upserts: int
  counts: dict[str, int]


@router.get("", response_model=BookingOutcomeListResponse, dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def list_booking_outcomes(
  outcome: Optional[str] = Query(None),
  agency_id: Optional[str] = Query(None),
  hotel_id: Optional[str] = Query(None),
  limit: int = Query(50, ge=1, le=200),
  db=Depends(get_db),
  user=Depends(get_current_user),
):
  """Minimal debug endpoint to inspect booking_outcomes."""
  org_id = user.get("organization_id")
  q: dict[str, Any] = {"organization_id": org_id}
  if outcome:
    q["final_outcome"] = outcome
  if agency_id:
    q["agency_id"] = agency_id
  if hotel_id:
    q["hotel_id"] = hotel_id

  cursor = db.booking_outcomes.find(q).sort("checkin_date", -1).limit(limit)
  docs = await cursor.to_list(length=limit)

  items: list[BookingOutcomeItem] = []
  for d in docs:
    items.append(
      BookingOutcomeItem(
        organization_id=str(d.get("organization_id")),
        booking_id=str(d.get("booking_id")),
        agency_id=str(d.get("agency_id") or ""),
        hotel_id=str(d.get("hotel_id") or ""),
        booked_at=(d.get("booked_at").isoformat() if d.get("booked_at") else None),
        checkin_date=(d.get("checkin_date").isoformat() if d.get("checkin_date") else None),
        final_outcome=d.get("final_outcome") or "unknown",
        outcome_source=d.get("outcome_source") or "rule_inferred",
        inferred_reason=d.get("inferred_reason"),
        verified=bool(d.get("verified")),
        verified_at=(d.get("verified_at").isoformat() if d.get("verified_at") else None),
        created_at=(d.get("created_at").isoformat() if d.get("created_at") else None),
        updated_at=(d.get("updated_at").isoformat() if d.get("updated_at") else None),
      )
    )

  return BookingOutcomeListResponse(ok=True, items=items)


@router.post("/recompute", response_model=BookingOutcomeRecomputeResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def recompute_booking_outcomes(
  days: int = Query(60, ge=1, le=365),
  dry_run: bool = Query(True),
  today: Optional[str] = Query(None, description="ISO timestamp for deterministic tests"),
  db=Depends(get_db),
  user=Depends(get_current_user),
):
  """Recompute booking_outcomes for org_demo (default org).

  - Restricts to organization 'default' (org_demo) for safety.
  - When dry_run=1 => does not write, only simulates counts.
  """
  org_id = user.get("organization_id")

  # Safety guard: only allow default/demo organization for now
  # (we identify default org by slug via organizations collection)
  org_doc = await db.organizations.find_one({"_id": org_id})
  if org_doc and org_doc.get("slug") not in {"default", "org_demo"}:
    return BookingOutcomeRecomputeResponse(ok=False, dry_run=dry_run, scanned=0, upserts=0, counts={})

  base_now = now_utc()
  if today:
    try:
      from datetime import datetime

      base_now = datetime.fromisoformat(today)
    except Exception:
      base_now = now_utc()

  cutoff = base_now - timedelta(days=days)
  q = {"organization_id": org_id, "created_at": {"$gte": cutoff}}

  cursor = db.bookings.find(q).sort("created_at", -1)
  scanned = 0
  upserts = 0
  counts: dict[str, int] = {}

  async for b in cursor:
    scanned += 1
    outcome, source, inferred = resolve_outcome_for_booking(b)
    counts[outcome] = counts.get(outcome, 0) + 1
    if not dry_run:
      await upsert_booking_outcome(db, b)
      upserts += 1

  return BookingOutcomeRecomputeResponse(ok=True, dry_run=dry_run, scanned=scanned, upserts=upserts, counts=counts)
