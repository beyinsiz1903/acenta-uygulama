from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from app.utils import now_utc


OPERATIONAL_REASONS = {"PRICE_CHANGED", "RATE_CHANGED", "HOTEL_OVERBOOK", "PAYMENT_FAILURE", "SUPPLIER_CANCELLED"}


@dataclass
class BookingOutcome:
  organization_id: str
  booking_id: str
  agency_id: str
  hotel_id: str
  booked_at: datetime
  checkin_date: Optional[datetime]
  final_outcome: str
  outcome_source: str
  inferred_reason: Optional[str]
  verified: bool
  verified_at: Optional[datetime]
  created_at: datetime
  updated_at: datetime
  # v2 fields
  outcome_version: int = 1
  evidence: list[dict[str, Any]] = field(default_factory=list)
  override: Optional[dict[str, Any]] = None
  confidence: float | None = None


def resolve_outcome_for_booking(doc: Dict[str, Any], today: Optional[datetime] = None) -> Tuple[str, str, Optional[str]]:
  if today is None:
    today = now_utc()

  status = doc.get("status") or "unknown"
  cancel_reason = (doc.get("cancel_reason") or "").upper()
  cancelled_by = (doc.get("cancelled_by") or "").lower()

  stay = doc.get("stay") or {}
  check_in = stay.get("check_in")
  inferred_reason: Optional[str] = None

  if isinstance(check_in, str):
    try:
      checkin_date = datetime.fromisoformat(check_in).date()
    except Exception:
      checkin_date = None
  elif isinstance(check_in, datetime):
    checkin_date = check_in.date()
  else:
    checkin_date = None

  # Rule 2: cancelled -> operational / behavioral
  if status == "cancelled":
    if cancel_reason in OPERATIONAL_REASONS or cancelled_by == "system":
      return "cancelled_operational", "rule_inferred", cancel_reason or None
    return "cancelled_behavioral", "rule_inferred", cancel_reason or None

  # Rule 3: no-show proxy: not cancelled, check-in geçmiş
  if status in {"confirmed", "pending"} and checkin_date is not None:
    yesterday = (today - timedelta(days=1)).date()
    if checkin_date <= yesterday:
      inferred_reason = "check_in_past_no_cancel"
      return "no_show", "rule_inferred", inferred_reason

  # Fallback
  return "unknown", "rule_inferred", inferred_reason


def apply_pms_status_evidence(
  outcome_doc: Dict[str, Any],
  *,
  status: str,
  at: datetime,
  source: str,
  ref: Optional[str] = None,
) -> Dict[str, Any]:
  """Apply a PMS status event as evidence to an existing outcome doc.

  - Appends a pms_status evidence record (idempotent by type+value+ref).
  - If status == 'arrived', sets final_outcome='arrived', outcome_source='pms_event',
    confidence=1.0 and outcome_version>=2.
  """
  status_norm = (status or "").lower()
  ev_list = outcome_doc.get("evidence") or []

  ev = {
    "type": "pms_status",
    "value": status_norm,
    "at": at.isoformat(),
    "source": source,
    "ref": ref,
  }

  # Idempotency: do not duplicate same evidence
  exists = any(
    (e or {}).get("type") == ev["type"]
    and (e or {}).get("value") == ev["value"]
    and (e or {}).get("ref") == ev["ref"]
    for e in ev_list
  )
  if not exists:
    ev_list.append(ev)

  outcome_doc["evidence"] = ev_list

  if status_norm == "arrived":
    outcome_doc["final_outcome"] = "arrived"
    outcome_doc["outcome_source"] = "pms_event"
    outcome_doc["outcome_version"] = max(int(outcome_doc.get("outcome_version") or 1), 2)
    outcome_doc["confidence"] = 1.0

  return outcome_doc


async def upsert_booking_outcome(db, booking_doc: Dict[str, Any], today: Optional[datetime] = None) -> Dict[str, Any]:
  org_id = booking_doc.get("organization_id")
  booking_id = str(booking_doc.get("_id"))
  if not org_id or not booking_id:
    raise ValueError("booking_doc must have organization_id and _id")

  stay = booking_doc.get("stay") or {}
  check_in = stay.get("check_in")
  if isinstance(check_in, str):
    try:
      checkin_date = datetime.fromisoformat(check_in).date()
    except Exception:
      checkin_date = None
  elif isinstance(check_in, datetime):
    checkin_date = check_in.date()
  else:
    checkin_date = None

  created_at = booking_doc.get("created_at")
  if isinstance(created_at, str):
    try:
      booked_at = datetime.fromisoformat(created_at)
    except Exception:
      booked_at = now_utc()
  elif isinstance(created_at, datetime):
    booked_at = created_at
  else:
    booked_at = now_utc()

  outcome, source, inferred_reason = resolve_outcome_for_booking(booking_doc, today=today)
  now = now_utc()

  # v2 defaults for new engine
  outcome_version = 2
  evidence: list[dict[str, Any]] = []
  # simple confidence mapping; can be refined in Story 2
  if source == "rule_inferred":
    if outcome == "unknown":
      confidence = 0.4
    else:
      confidence = 0.8
  else:
    # non-rule sources (e.g. pms_event) are considered strong
    confidence = 1.0

  # MongoDB requires datetime for date-like fields; normalize checkin_date
  checkin_dt: Optional[datetime]
  if checkin_date is None:
    checkin_dt = None
  else:
    checkin_dt = datetime.combine(checkin_date, datetime.min.time(), tzinfo=timezone.utc)

  doc = {
    "organization_id": org_id,
    "booking_id": booking_id,
    "agency_id": str(booking_doc.get("agency_id") or ""),
    "hotel_id": str(booking_doc.get("hotel_id") or ""),
    "booked_at": booked_at,
    "checkin_date": checkin_dt,
    "final_outcome": outcome,
    "outcome_source": source,
    "inferred_reason": inferred_reason,
    "verified": False,
    "verified_at": None,
    "outcome_version": outcome_version,
    "evidence": evidence,
    "override": None,
    "confidence": confidence,
    "updated_at": now,
  }

  await db.booking_outcomes.update_one(
    {"organization_id": org_id, "booking_id": booking_id},
    {"$set": doc, "$setOnInsert": {"created_at": now}},
    upsert=True,
  )

  return doc
