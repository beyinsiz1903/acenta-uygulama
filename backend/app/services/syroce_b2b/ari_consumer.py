"""Channel B — Syroce PMS ARI consumer (Redis Streams).

The PMS pushes real-time ARI (Availability / Rate / Restriction) events to a
single stream this agency is allowed to read:

    b2b:tenant:{SYROCE_TENANT_ID}:agency:{SYROCE_AGENCY_ID}:ari:v1

Consumption model (at-least-once):
  - XGROUP CREATE <stream> agency-consumers $ MKSTREAM   (idempotent)
  - on (re)connect: drain this consumer's PENDING with id "0" first, so we
    resume from the last un-ACKed entry rather than losing anything.
  - XREADGROUP GROUP agency-consumers <consumer> COUNT 100 BLOCK 5000 ... ">"
  - apply -> XACK. Only ACK AFTER a successful apply (failed applies are left
    pending for redelivery).
  - periodic XAUTOCLAIM to take over entries stranded by dead consumers.

Idempotency: the same event_id may arrive multiple times. We apply keyed on
(room_type_code, date_from..date_to[, event_type]) and order by created_at so
the newest event wins (last-write-wins). The PMS is authoritative.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.services.syroce_b2b.config import get_b2b_config

logger = logging.getLogger("syroce_b2b.ari")

GROUP = "agency-consumers"
STATE_COLLECTION = "syroce_ari_state"

_BLOCK_MS = 5000
_BATCH = 100
_AUTOCLAIM_MIN_IDLE_MS = 60_000   # reclaim entries idle > 60s
_AUTOCLAIM_EVERY_S = 30.0
_RECONNECT_BACKOFF_S = 5.0


def _consumer_name() -> str:
    return f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"


def _parse_created_at(raw: Any) -> datetime:
    """Parse an event created_at into an aware datetime (epoch fallback)."""
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(float(raw), tz=timezone.utc)
    if isinstance(raw, str) and raw:
        txt = raw.strip()
        try:
            dt = datetime.fromisoformat(txt.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                return datetime.fromtimestamp(float(txt), tz=timezone.utc)
            except (TypeError, ValueError):
                pass
    # Unknown / missing -> oldest possible so any later, parseable event wins.
    return datetime.min.replace(tzinfo=timezone.utc)


def _state_key(tenant_id: str, agency_id: str, fields: Dict[str, str]) -> str:
    room = fields.get("room_type_code") or "*"
    df = fields.get("date_from") or "*"
    dt = fields.get("date_to") or "*"
    etype = fields.get("event_type") or "*"
    rate_plan = fields.get("rate_plan_code") or "*"
    return f"{tenant_id}:{agency_id}:{etype}:{room}:{rate_plan}:{df}:{dt}"


class AriConsumer:
    """Long-running consumer for one agency's ARI stream."""

    def __init__(self) -> None:
        self.cfg = get_b2b_config()
        self.consumer = _consumer_name()
        self._stop = asyncio.Event()
        self._last_autoclaim = 0.0
        self._autoclaim_cursor = "0-0"

    def stop(self) -> None:
        self._stop.set()

    # ── apply ────────────────────────────────────────────────────

    async def _apply(self, db, fields: Dict[str, str]) -> None:
        """Idempotently apply one ARI event (last-write-wins by created_at)."""
        tenant_id = self.cfg.tenant_id
        agency_id = self.cfg.agency_id
        key = _state_key(tenant_id, agency_id, fields)
        created_at = _parse_created_at(fields.get("created_at"))

        payload: Dict[str, Any] = {}
        raw_payload = fields.get("payload")
        if isinstance(raw_payload, str) and raw_payload:
            try:
                payload = json.loads(raw_payload)
            except ValueError:
                payload = {"_raw": raw_payload}

        doc = {
            "_id": key,
            "tenant_id": tenant_id,
            "agency_id": agency_id,
            "schema": fields.get("schema") or "ari.v1",
            "event_type": fields.get("event_type"),
            "room_type_code": fields.get("room_type_code"),
            "rate_plan_code": fields.get("rate_plan_code"),
            "date_from": fields.get("date_from"),
            "date_to": fields.get("date_to"),
            "price": payload.get("price"),
            "currency": payload.get("currency"),
            "stop_sale": payload.get("stop_sale"),
            "available_rooms": payload.get("available_rooms"),
            "payload": payload,
            "created_at": created_at,
            "last_event_id": fields.get("event_id"),
            "applied_at": datetime.now(timezone.utc),
        }

        # Last-write-wins: only overwrite when the incoming event is newer or
        # equal. matched_count==0 means either no doc yet OR the stored doc is
        # newer; the insert then either creates it or loses the race (stale -> drop).
        res = await db[STATE_COLLECTION].update_one(
            {"_id": key, "created_at": {"$lte": created_at}},
            {"$set": doc},
        )
        if res.matched_count == 0:
            try:
                await db[STATE_COLLECTION].insert_one(doc)
            except Exception:
                # Existing doc is strictly newer -> drop this stale event (LWW).
                logger.debug("syroce_b2b ARI stale event dropped key=%s", key)

    async def _handle_entries(self, db, entries: List[Tuple[str, Dict[str, str]]], redis, stream: str) -> int:
        """Apply a batch and ACK each entry that applied successfully."""
        acked = 0
        for entry_id, fields in entries:
            try:
                await self._apply(db, fields)
            except Exception:
                # Do NOT ack -> entry stays pending for redelivery (at-least-once).
                logger.exception("syroce_b2b ARI apply failed id=%s (left pending)", entry_id)
                continue
            try:
                await redis.xack(stream, GROUP, entry_id)
                acked += 1
            except Exception:
                logger.warning("syroce_b2b ARI xack failed id=%s", entry_id)
        return acked

    # ── stream plumbing ──────────────────────────────────────────

    @staticmethod
    def _normalize(raw_entries) -> List[Tuple[str, Dict[str, str]]]:
        out: List[Tuple[str, Dict[str, str]]] = []
        for entry_id, fields in raw_entries or []:
            out.append((entry_id, dict(fields or {})))
        return out

    async def _ensure_group(self, redis, stream: str) -> None:
        try:
            await redis.xgroup_create(stream, GROUP, id="$", mkstream=True)
            logger.info("syroce_b2b ARI created consumer group on %s", stream)
        except Exception as exc:
            # BUSYGROUP -> already exists; anything else re-raises.
            if "BUSYGROUP" not in str(exc):
                raise

    async def _drain_pending(self, db, redis, stream: str) -> None:
        """Reprocess this consumer's already-delivered-but-un-ACKed entries."""
        resp = await redis.xreadgroup(
            GROUP, self.consumer, {stream: "0"}, count=_BATCH
        )
        for _stream_name, raw_entries in resp or []:
            entries = self._normalize(raw_entries)
            if entries:
                await self._handle_entries(db, entries, redis, stream)

    async def _autoclaim(self, db, redis, stream: str) -> None:
        """Take over entries stranded by crashed/dead consumers."""
        try:
            cursor, raw_entries, _deleted = await redis.xautoclaim(
                stream, GROUP, self.consumer,
                min_idle_time=_AUTOCLAIM_MIN_IDLE_MS,
                start_id=self._autoclaim_cursor,
                count=_BATCH,
            )
            self._autoclaim_cursor = cursor or "0-0"
            entries = self._normalize(raw_entries)
            if entries:
                logger.info("syroce_b2b ARI autoclaimed %d stranded entries", len(entries))
                await self._handle_entries(db, entries, redis, stream)
        except Exception as exc:
            logger.warning("syroce_b2b ARI xautoclaim error: %s", exc)

    # ── main loop ────────────────────────────────────────────────

    async def run(self) -> None:
        cfg = self.cfg
        if not cfg.stream_ready:
            logger.info(
                "syroce_b2b ARI consumer dormant — not configured "
                "(SYROCE_REDIS_URL / SYROCE_TENANT_ID / SYROCE_AGENCY_ID missing)."
            )
            return

        stream = cfg.stream_name
        logger.info("syroce_b2b ARI consumer starting stream=%s consumer=%s", stream, self.consumer)

        try:
            import redis.asyncio as aioredis
        except Exception:
            logger.warning("syroce_b2b ARI consumer: redis library unavailable.")
            return

        from app.db import get_db

        while not self._stop.is_set():
            redis = None
            try:
                redis = aioredis.from_url(
                    cfg.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=10,
                )
                await redis.ping()
                db = await get_db()
                await self._ensure_group(redis, stream)
                # Resume from the last un-ACKed entry before reading new ones.
                await self._drain_pending(db, redis, stream)
                logger.info("syroce_b2b ARI consumer connected stream=%s", stream)

                while not self._stop.is_set():
                    resp = await redis.xreadgroup(
                        GROUP, self.consumer, {stream: ">"},
                        count=_BATCH, block=_BLOCK_MS,
                    )
                    for _stream_name, raw_entries in resp or []:
                        entries = self._normalize(raw_entries)
                        if entries:
                            await self._handle_entries(db, entries, redis, stream)

                    now = asyncio.get_event_loop().time()
                    if now - self._last_autoclaim >= _AUTOCLAIM_EVERY_S:
                        self._last_autoclaim = now
                        await self._autoclaim(db, redis, stream)

            except asyncio.CancelledError:
                logger.info("syroce_b2b ARI consumer cancelled.")
                raise
            except Exception as exc:
                logger.warning("syroce_b2b ARI consumer error (reconnecting): %s", exc)
                await asyncio.sleep(_RECONNECT_BACKOFF_S)
            finally:
                if redis is not None:
                    try:
                        await redis.aclose()
                    except Exception:
                        pass

        logger.info("syroce_b2b ARI consumer stopped.")


# ── lifecycle integration ────────────────────────────────────────

_consumer: Optional[AriConsumer] = None
_task: Optional[asyncio.Task] = None


def start_ari_consumer() -> None:
    """Start the ARI consumer as a background task (no-op if unconfigured)."""
    global _consumer, _task
    cfg = get_b2b_config()
    if not cfg.stream_ready:
        logger.info("syroce_b2b ARI consumer not started — integration not configured.")
        return
    if _task is not None and not _task.done():
        return
    _consumer = AriConsumer()
    _task = asyncio.create_task(_consumer.run(), name="syroce-b2b-ari-consumer")
    logger.info("syroce_b2b ARI consumer task scheduled.")


async def stop_ari_consumer() -> None:
    """Signal and await graceful shutdown of the ARI consumer."""
    global _consumer, _task
    if _consumer is not None:
        _consumer.stop()
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):
            pass
    _consumer = None
    _task = None


def consumer_running() -> bool:
    return _task is not None and not _task.done()


__all__ = ["AriConsumer", "start_ari_consumer", "stop_ari_consumer", "consumer_running"]
