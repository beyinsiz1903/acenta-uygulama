from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.booking_outcomes import OPERATIONAL_REASONS, resolve_outcome_for_booking, upsert_booking_outcome, apply_pms_status_evidence
from app.services.audit import write_audit_log
from app.utils import now_utc

router = APIRouter(prefix="/admin/booking-outcomes", tags=["admin-booking-outcomes"])


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


class BookingOutcomePmsEventIn(BaseModel):
  status: str
  at: str
  source: str = "pms:mock"
  ref: Optional[str] = None


class BookingOutcomePmsEventResponse(BaseModel):
  ok: bool = True
  booking_id: str
  final_outcome: str
  outcome_source: str
  outcome_version: int
  confidence: float | None = None
  evidence_count: int


class BookingOutcomeVerifyIn(BaseModel):
  final_outcome: Optional[str] = None
  note: Optional[str] = None


class BookingOutcomeOverrideIn(BaseModel):
  final_outcome: str
  reason: Optional[str] = None


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


@router.post("/{booking_id}/pms-event", response_model=BookingOutcomePmsEventResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def apply_pms_event(
  booking_id: str,
  payload: BookingOutcomePmsEventIn,
  db=Depends(get_db),
  user=Depends(get_current_user),
):
  """Deterministic admin/debug endpoint to simulate a PMS status event.

  - Finds the booking in db.bookings for current org.
  - Upserts a booking_outcomes doc if needed.
  - Applies pms_status evidence and, for status='arrived', marks outcome as arrived.
  """
  org_id = user.get("organization_id")

  booking = await db.bookings.find_one({"organization_id": org_id, "_id": booking_id})
  if not booking:
    # allow also lookup by stringified _id if needed
    from bson import ObjectId

    try:
      oid = ObjectId(booking_id)
    except Exception:
      raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")
    booking = await db.bookings.find_one({"organization_id": org_id, "_id": oid})
    if not booking:
      raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

  # Ensure there is an outcome doc
  await upsert_booking_outcome(db, booking)
  outcome_doc = await db.booking_outcomes.find_one({"organization_id": org_id, "booking_id": str(booking.get("_id"))}) or {}

  # Parse timestamp
  from datetime import datetime

  try:
    at_dt = datetime.fromisoformat(payload.at)
  except Exception:
    raise HTTPException(status_code=422, detail="INVALID_AT_TIMESTAMP")

  updated = apply_pms_status_evidence(
    outcome_doc,
    status=payload.status,
    at=at_dt,
    source=payload.source,
    ref=payload.ref,
  )

  # Persist updated outcome
  await db.booking_outcomes.update_one(
    {"organization_id": org_id, "booking_id": updated["booking_id"]},
    {"$set": updated},
    upsert=True,
  )

  # Return response
  evidence = updated.get("evidence") or []
  return BookingOutcomePmsEventResponse(
    ok=True,
    booking_id=updated["booking_id"],
    final_outcome=updated.get("final_outcome") or "unknown",
    outcome_source=updated.get("outcome_source") or "rule_inferred",
    outcome_version=int(updated.get("outcome_version") or 1),
    confidence=updated.get("confidence"),
    evidence_count=len(evidence),
  )



@router.post("/{booking_id}/verify", dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def verify_booking_outcome(
  booking_id: str,
  payload: BookingOutcomeVerifyIn,
  request: Request,
  db=Depends(get_db),
  user=Depends(get_current_user),
):
  org_id = user.get("organization_id")

  doc = await db.booking_outcomes.find_one({"organization_id": org_id, "booking_id": booking_id})
  if not doc:
    raise HTTPException(status_code=404, detail="BOOKING_OUTCOME_NOT_FOUND")

  before = doc.copy()

  now = now_utc()
  email = user.get("email")

  # Apply verify flags
  doc["verified"] = True
  doc["verified_by_email"] = email
  doc["verified_at"] = now

  if payload.final_outcome:
    doc["final_outcome"] = payload.final_outcome
    doc["outcome_source"] = "manual_verified"

  # Append manual_verify evidence
  ev_list = doc.get("evidence") or []
  ev_list.append(
    {
      "type": "manual_verify",
      "by_email": email,
      "note": payload.note,
      "at": now.isoformat(),
    }
  )
  doc["evidence"] = ev_list

  # Confidence & version tweaks for manual verification
  doc["outcome_version"] = max(int(doc.get("outcome_version") or 1), 2)
  if doc.get("outcome_source") == "manual_verified":
    doc["confidence"] = 0.95

  await db.booking_outcomes.update_one(
    {"organization_id": org_id, "booking_id": booking_id},
    {"$set": doc},
    upsert=True,
  )

  after = await db.booking_outcomes.find_one({"organization_id": org_id, "booking_id": booking_id}) or {}

  actor = {"email": email, "roles": user.get("roles", [])}

  await write_audit_log(
    db,
    organization_id=org_id,
    actor=actor,
    request=request,
    action="booking_outcome.verified",
    target_type="booking_outcome",
    target_id=booking_id,
    before=before,
    after=after,
    meta={"note": payload.note},
  )

  evidence = after.get("evidence") or []

  return {
    "ok": True,
    "booking_id": booking_id,
    "final_outcome": after.get("final_outcome") or "unknown",
    "outcome_source": after.get("outcome_source") or "rule_inferred",
    "verified": bool(after.get("verified")),
    "verified_by_email": after.get("verified_by_email"),
    "verified_at": after.get("verified_at").isoformat() if after.get("verified_at") else None,
    "evidence_count": len(evidence),
    "outcome_version": int(after.get("outcome_version") or 1),
  }


@router.post("/{booking_id}/override", dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def override_booking_outcome(
  booking_id: str,
  payload: BookingOutcomeOverrideIn,
  request: Request,
  db=Depends(get_db),
  user=Depends(get_current_user),
):
  org_id = user.get("organization_id")

  doc = await db.booking_outcomes.find_one({"organization_id": org_id, "booking_id": booking_id})
  if not doc:
    raise HTTPException(status_code=404, detail="BOOKING_OUTCOME_NOT_FOUND")

  before = doc.copy()

  now = now_utc()
  email = user.get("email")

  # Apply override structure
  override = {
    "final_outcome": payload.final_outcome,
    "reason": payload.reason,
    "by_email": email,
    "at": now.isoformat(),
  }
  doc["override"] = override

  # Apply final outcome + manual override source
  doc["final_outcome"] = payload.final_outcome
  doc["outcome_source"] = "manual_override"
  doc["verified"] = True
  doc["verified_by_email"] = email
  doc["verified_at"] = now

  # Append manual_override evidence
  ev_list = doc.get("evidence") or []
  ev_list.append(
    {
      "type": "manual_override",
      "by_email": email,
      "reason": payload.reason,
      "at": now.isoformat(),
    }
  )
  doc["evidence"] = ev_list

  # v2 semantics
  doc["outcome_version"] = max(int(doc.get("outcome_version") or 1), 2)
  doc["confidence"] = 1.0

  await db.booking_outcomes.update_one(
    {"organization_id": org_id, "booking_id": booking_id},
    {"$set": doc},
    upsert=True,
  )

  after = await db.booking_outcomes.find_one({"organization_id": org_id, "booking_id": booking_id}) or {}

  actor = {"email": email, "roles": user.get("roles", [])}

  await write_audit_log(
    db,
    organization_id=org_id,
    actor=actor,
    request=request,
    action="booking_outcome.overridden",
    target_type="booking_outcome",
    target_id=booking_id,
    before=before,
    after=after,
    meta={"reason": payload.reason},
  )

  evidence = after.get("evidence") or []

  return {
    "ok": True,
    "booking_id": booking_id,
    "final_outcome": after.get("final_outcome") or "unknown",
    "outcome_source": after.get("outcome_source") or "rule_inferred",
    "verified": bool(after.get("verified")),
    "override": after.get("override"),
    "outcome_version": int(after.get("outcome_version") or 1),
    "evidence_count": len(evidence),
  }
