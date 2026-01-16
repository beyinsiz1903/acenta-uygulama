from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List

import httpx

from app.errors import AppError
from app.utils import now_utc


def _parse_ical_date(value: str) -> date:
    """Parse common iCal date formats into a date.

    Supports:
    - YYYYMMDD (e.g. 20260115)
    - YYYY-MM-DD
    - Full ISO timestamps (date part is used)
    """

    v = (value or "").strip()
    if not v:
        raise ValueError("empty date value")

    # Basic date (e.g. 20260115)
    if len(v) == 8 and v.isdigit():
        return datetime.strptime(v, "%Y%m%d").date()

    # ISO date (e.g. 2026-01-15)
    if len(v) == 10 and v[4] == "-" and v[7] == "-":
        return datetime.strptime(v, "%Y-%m-%d").date()

    # Fallback: try fromisoformat and drop time
    return datetime.fromisoformat(v).date()


def _parse_ical_events(text: str) -> List[Dict[str, Any]]:
    """Very small iCal parser for all-day VEVENTs.

    We intentionally support only the subset we need:
    - BEGIN:VEVENT / END:VEVENT blocks
    - UID
    - DTSTART / DTEND (DATE or DATE-TIME)

    RRULE / EXDATE gibi gelişmiş özellikler v1 için kapsam dışı.
    """

    events: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None
    in_event = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line == "BEGIN:VEVENT":
            in_event = True
            current = {}
            continue
        if line == "END:VEVENT":
            if in_event and current and {"uid", "dtstart", "dtend"} <= current.keys():
                events.append(current)
            in_event = False
            current = None
            continue

        if not in_event or current is None:
            continue

        # Property lines like KEY:VALUE or KEY;PARAM=...:VALUE
        if ":" not in line:
            continue
        key_part, value = line.split(":", 1)
        key = key_part.split(";", 1)[0].upper()
        value = value.strip()

        if key == "UID":
            current["uid"] = value
        elif key == "DTSTART":
            current["dtstart"] = value
        elif key == "DTEND":
            current["dtend"] = value

    return events


async def _fetch_ical_text(url: str, timeout: float = 15.0) -> str:
    """Fetch iCal text.

    For test environments we support a special `mock://` scheme so that
    we don't depend on external network availability.
    """

    if url.startswith("mock://"):
        # Very small static calendar: blocks 10-12th of current month
        today = now_utc().date()
        start = today.replace(day=10)
        end = today.replace(day=13)  # DTEND is conventionally checkout / exclusive
        return f"""BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:mock-1\nDTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}\nDTEND;VALUE=DATE:{end.strftime('%Y%m%d')}\nEND:VEVENT\nEND:VCALENDAR\n"""

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(url)
        except httpx.RequestError as exc:  # type: ignore[no-untyped-call]
            raise AppError(502, "ical_fetch_failed", f"iCal fetch error: {exc}") from exc

    if resp.status_code != 200:
        raise AppError(502, "ical_fetch_failed", f"iCal fetch status {resp.status_code}")

    return resp.text


async def sync_ical_feed(db, feed: Dict[str, Any]) -> Dict[str, Any]:
    """Download an iCal file for a feed and materialize availability blocks.

    - Deletes previous blocks for this (organization_id, product_id, feed_id)
    - Inserts new blocks based on DTSTART/DTEND pairs
    - Updates feed.last_sync_at
    """

    organization_id = feed["organization_id"]
    product_id = feed["product_id"]
    feed_id = feed["id"]
    url = feed["url"]

    ical_text = await _fetch_ical_text(url)
    events = _parse_ical_events(ical_text)

    # Remove existing blocks for this feed
    await db.availability_blocks.delete_many(
        {
            "organization_id": organization_id,
            "product_id": product_id,
            "source": "ical",
            "source_ref.feed_id": feed_id,
        }
    )

    docs: List[Dict[str, Any]] = []
    for ev in events:
        try:
            start_date = _parse_ical_date(ev["dtstart"])
            end_date = _parse_ical_date(ev["dtend"])
        except Exception:
            # Skip malformed events silently for v1
            continue

        if end_date < start_date:
            continue

        docs.append(
            {
                "id": f"{feed_id}:{ev['uid']}",
                "organization_id": organization_id,
                "product_id": product_id,
                "source": "ical",
                "source_ref": {"feed_id": feed_id, "uid": ev["uid"]},
                # Store as ISO date strings to avoid ObjectId/serialization issues
                "date_from": start_date.isoformat(),
                "date_to": end_date.isoformat(),
                "created_at": now_utc().isoformat(),
            }
        )

    if docs:
        await db.availability_blocks.insert_many(docs)

    await db.ical_feeds.update_one(
        {"id": feed_id, "organization_id": organization_id},
        {"$set": {"last_sync_at": now_utc().isoformat()}},
    )

    return {
        "feed_id": feed_id,
        "events": len(events),
        "blocks_created": len(docs),
    }
