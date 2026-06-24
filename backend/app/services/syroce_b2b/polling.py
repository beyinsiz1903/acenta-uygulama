"""REST polling service (Scenario B real-time path).

The PMS is authoritative. Since Redis Streams are unreachable from a separate
Replit project, we periodically poll ``/availability`` and ``/rates`` and apply
the results to a local table with **last-write-wins** keyed by
``(room_type, date range)``.

The service is dormant until the integration is CONNECTED and polling is enabled
in the connection store. It never raises into the event loop — errors are logged
and recorded, and the loop backs off and retries.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.services.syroce_b2b import connection_store as store

logger = logging.getLogger("syroce_b2b.polling")

LOCAL_COLLECTION = "syroce_b2b_local_ari"
_MIN_INTERVAL_S = 30.0
_ERROR_BACKOFF_S = 60.0


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _iso(d: date) -> str:
    return d.isoformat()


def _state_key(room_type: str, date_from: str, date_to: str) -> str:
    return f"{room_type or '*'}|{date_from}|{date_to}"


async def _upsert_lww(doc: Dict[str, Any]) -> None:
    """Last-write-wins upsert keyed by (room_type, date range).

    A polling cycle is always the freshest source for the window it queried, so we
    gate the write on ``synced_at`` to stay safe under concurrent/overlapping
    cycles. ``matched_count == 0`` means no doc yet OR the stored one is newer;
    the insert then either creates it or (on a duplicate) loses the race — and we
    re-raise any non-duplicate DB error so the caller can record/retry.
    """
    db = await get_db()
    key = doc["_id"]
    synced_at = doc["synced_at"]
    res = await db[LOCAL_COLLECTION].update_one(
        {"_id": key, "synced_at": {"$lte": synced_at}},
        {"$set": doc},
    )
    if res.matched_count == 0:
        try:
            await db[LOCAL_COLLECTION].insert_one(doc)
        except Exception as exc:  # pragma: no cover - exercised under races
            from pymongo.errors import DuplicateKeyError

            if isinstance(exc, DuplicateKeyError):
                # Stored doc is strictly newer -> drop this stale write (LWW).
                logger.debug("syroce_b2b polling stale write dropped key=%s", key)
            else:
                raise


async def sync_once() -> Dict[str, Any]:
    """Run one availability + rates poll and apply results locally (LWW).

    Returns a small non-secret summary. Raises only on configuration/connection
    problems; transport/PMS errors are surfaced to the caller for handling.
    """
    from app.services.syroce_b2b.client import SyroceB2BClient

    settings = await store.get_poll_settings()
    horizon = int(settings.get("poll_horizon_days") or 30)
    room_types: List[Optional[str]] = settings.get("poll_room_types") or [None]
    if not room_types:
        room_types = [None]

    check_in = _today()
    check_out = check_in + timedelta(days=horizon)
    ci, co = _iso(check_in), _iso(check_out)

    client = await SyroceB2BClient.load()
    now = datetime.now(timezone.utc)
    written = 0
    agency_id = await store.get_agency_id()

    for rt in room_types:
        avail = await client.get_availability(check_in=ci, check_out=co, room_type=rt)
        rates = await client.get_rates(start_date=ci, end_date=co, room_type=rt)

        rate_index: Dict[str, Any] = {}
        for r in (rates.get("rates") or rates.get("room_types") or []):
            if isinstance(r, dict) and r.get("room_type"):
                rate_index[r["room_type"]] = r

        for room in (avail.get("room_types") or []):
            if not isinstance(room, dict):
                continue
            rtype = room.get("room_type") or rt or "*"
            key = _state_key(rtype, ci, co)
            await _upsert_lww(
                {
                    "_id": key,
                    "agency_id": agency_id,
                    "room_type": rtype,
                    "date_from": ci,
                    "date_to": co,
                    "available_rooms": room.get("available_rooms"),
                    "total_rooms": room.get("total_rooms"),
                    "base_price": room.get("base_price"),
                    "capacity": room.get("capacity"),
                    "rate": rate_index.get(rtype),
                    "source": "polling",
                    "synced_at": now,
                }
            )
            written += 1

    return {"written": written, "check_in": ci, "check_out": co, "synced_at": now}


# ── background loop ──────────────────────────────────────────────────

class PollingService:
    def __init__(self) -> None:
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        logger.info("syroce_b2b polling service started.")
        while not self._stop.is_set():
            interval = _MIN_INTERVAL_S
            try:
                if not await store.is_connected():
                    interval = 60.0
                else:
                    settings = await store.get_poll_settings()
                    interval = max(_MIN_INTERVAL_S, float(settings.get("poll_interval_seconds") or 300))
                    if settings.get("poll_enabled"):
                        summary = await sync_once()
                        logger.info("syroce_b2b polling cycle wrote %d rows.", summary.get("written", 0))
                    else:
                        interval = 60.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("syroce_b2b polling cycle error: %s", exc)
                try:
                    await store.record_error(f"polling: {exc}")
                except Exception:
                    pass
                interval = _ERROR_BACKOFF_S

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
        logger.info("syroce_b2b polling service stopped.")


_service: Optional[PollingService] = None
_task: Optional[asyncio.Task] = None


def start_polling() -> None:
    """Start the polling loop as a background task (always safe; self-gates)."""
    global _service, _task
    from app.services.syroce_b2b.config import get_b2b_config

    if not get_b2b_config().base_ready:
        logger.info("syroce_b2b polling not started — SYROCE_B2B_BASE_URL not set.")
        return
    if _task is not None and not _task.done():
        return
    _service = PollingService()
    _task = asyncio.create_task(_service.run(), name="syroce-b2b-polling")
    logger.info("syroce_b2b polling task scheduled.")


async def stop_polling() -> None:
    global _service, _task
    if _service is not None:
        _service.stop()
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):
            pass
    _service = None
    _task = None


def polling_running() -> bool:
    return _task is not None and not _task.done()


__all__ = [
    "LOCAL_COLLECTION",
    "sync_once",
    "PollingService",
    "start_polling",
    "stop_polling",
    "polling_running",
]
