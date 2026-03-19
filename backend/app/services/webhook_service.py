"""Webhook Service — Core business logic for productized webhook system.

Responsibilities:
  - Subscription management (CRUD, duplicate policy, secret rotation)
  - HMAC-SHA256 signing
  - URL validation + SSRF protection
  - Delivery creation, retry scheduling, idempotency
  - Circuit breaker per endpoint
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger("services.webhook")

# ── Constants ────────────────────────────────────────────────

WEBHOOK_SECRET_PREFIX = "whsec_"
MAX_SUBSCRIPTIONS_PER_ORG = 10
WEBHOOK_TIMEOUT_SECONDS = 10
MAX_RETRY_ATTEMPTS = 6

# Retry delays in seconds: immediate, 1m, 5m, 15m, 1h, 6h
RETRY_DELAYS = [0, 60, 300, 900, 3600, 21600]

ALLOWED_EVENTS = [
    "booking.created",
    "booking.quoted",
    "booking.optioned",
    "booking.confirmed",
    "booking.cancelled",
    "booking.completed",
    "booking.refunded",
    "invoice.created",
    "payment.received",
    "payment.refunded",
]

# SSRF protection — blocked IP ranges
_BLOCKED_RANGES = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6 private ranges
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


# ── Secret Management ────────────────────────────────────────

def generate_secret() -> str:
    """Generate a webhook signing secret."""
    raw = secrets.token_hex(32)
    return f"{WEBHOOK_SECRET_PREFIX}{raw}"


def mask_secret(secret: str) -> str:
    """Mask a secret for display — show prefix + last 4 chars."""
    if len(secret) <= 10:
        return "****"
    return f"{secret[:6]}****{secret[-4:]}"


# ── HMAC Signing ─────────────────────────────────────────────

def compute_signature(secret: str, timestamp: int, payload_json: str) -> str:
    """Compute HMAC-SHA256 signature for webhook delivery.

    signature = HMAC-SHA256(secret, "{timestamp}.{payload}")
    """
    message = f"{timestamp}.{payload_json}"
    sig = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={sig}"


def verify_signature(secret: str, timestamp: int, payload_json: str, signature: str) -> bool:
    """Verify a webhook signature (for documentation / SDK reference)."""
    expected = compute_signature(secret, timestamp, payload_json)
    return hmac.compare_digest(expected, signature)


# ── URL Validation + SSRF Protection ─────────────────────────

def validate_webhook_url(url: str) -> tuple[bool, str]:
    """Validate a webhook URL — HTTPS only, no private/metadata IPs.

    Returns (is_valid, error_message).
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    # Must be HTTPS
    if parsed.scheme != "https":
        return False, "Only HTTPS URLs are accepted"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must have a hostname"

    # Block localhost variations
    localhost_patterns = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    if hostname.lower() in localhost_patterns:
        return False, "Localhost URLs are not allowed"

    # Block metadata endpoints (AWS, GCP, Azure)
    metadata_hosts = {"169.254.169.254", "metadata.google.internal", "metadata.google.com"}
    if hostname.lower() in metadata_hosts:
        return False, "Metadata service URLs are not allowed"

    # Try to resolve and check IP ranges
    try:
        import socket
        addrs = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addrs:
            ip = ipaddress.ip_address(sockaddr[0])
            for blocked in _BLOCKED_RANGES:
                if ip in blocked:
                    return False, f"URL resolves to blocked IP range ({blocked})"
    except socket.gaierror:
        # DNS resolution failed — we allow it (might resolve at delivery time)
        pass
    except Exception:
        pass

    # Must have a path (or default /)
    if not parsed.path:
        parsed = parsed._replace(path="/")

    return True, ""


# ── Subscription Operations ──────────────────────────────────

async def create_subscription(
    db,
    organization_id: str,
    target_url: str,
    subscribed_events: list[str],
    description: str = "",
    created_by: str = "",
) -> tuple[Optional[dict], str]:
    """Create a webhook subscription.

    Returns (subscription_dict_with_plain_secret, error_message).
    Secret is returned in plaintext ONLY on create.
    """
    # Validate URL
    valid, err = validate_webhook_url(target_url)
    if not valid:
        return None, err

    # Validate events
    invalid_events = [e for e in subscribed_events if e not in ALLOWED_EVENTS]
    if invalid_events:
        return None, f"Invalid event types: {', '.join(invalid_events)}"

    if not subscribed_events:
        return None, "At least one event type must be subscribed"

    # Check org subscription limit
    active_count = await db.webhook_subscriptions.count_documents({
        "organization_id": organization_id,
        "is_active": True,
    })
    if active_count >= MAX_SUBSCRIPTIONS_PER_ORG:
        return None, f"Maximum {MAX_SUBSCRIPTIONS_PER_ORG} active subscriptions per organization"

    # Check duplicate (same org + URL + event set)
    sorted_events = sorted(subscribed_events)
    existing = await db.webhook_subscriptions.find_one({
        "organization_id": organization_id,
        "target_url": target_url,
        "subscribed_events": sorted_events,
        "is_active": True,
    })
    if existing:
        return None, "A subscription with this URL and event set already exists"

    # Generate secret
    plain_secret = generate_secret()
    now = datetime.now(timezone.utc)
    subscription_id = str(uuid.uuid4())

    doc = {
        "subscription_id": subscription_id,
        "organization_id": organization_id,
        "target_url": target_url,
        "subscribed_events": sorted_events,
        "secret": plain_secret,
        "is_active": True,
        "description": description,
        "created_by": created_by,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "circuit_state": "closed",
        "consecutive_failures": 0,
    }

    await db.webhook_subscriptions.insert_one(doc)

    # Return with plaintext secret (only time it's shown)
    result = {k: v for k, v in doc.items() if k != "_id"}
    result["secret"] = plain_secret  # Full secret — shown once
    return result, ""


async def get_subscription(db, subscription_id: str, organization_id: str) -> Optional[dict]:
    """Get a subscription by ID (secret masked)."""
    doc = await db.webhook_subscriptions.find_one(
        {"subscription_id": subscription_id, "organization_id": organization_id},
        {"_id": 0},
    )
    if doc:
        doc["secret"] = mask_secret(doc.get("secret", ""))
    return doc


async def list_subscriptions(db, organization_id: str) -> list[dict]:
    """List all subscriptions for an organization (secrets masked)."""
    cursor = db.webhook_subscriptions.find(
        {"organization_id": organization_id},
        {"_id": 0},
    ).sort("created_at", -1)

    subs = []
    async for doc in cursor:
        doc["secret"] = mask_secret(doc.get("secret", ""))
        subs.append(doc)
    return subs


async def update_subscription(
    db,
    subscription_id: str,
    organization_id: str,
    updates: dict,
) -> tuple[Optional[dict], str]:
    """Update a webhook subscription. Returns (updated_doc, error)."""
    allowed_fields = {"target_url", "subscribed_events", "is_active", "description"}
    clean = {k: v for k, v in updates.items() if k in allowed_fields}

    if "target_url" in clean:
        valid, err = validate_webhook_url(clean["target_url"])
        if not valid:
            return None, err

    if "subscribed_events" in clean:
        invalid_events = [e for e in clean["subscribed_events"] if e not in ALLOWED_EVENTS]
        if invalid_events:
            return None, f"Invalid event types: {', '.join(invalid_events)}"
        clean["subscribed_events"] = sorted(clean["subscribed_events"])

    clean["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.webhook_subscriptions.find_one_and_update(
        {"subscription_id": subscription_id, "organization_id": organization_id},
        {"$set": clean},
        return_document=True,
    )
    if not result:
        return None, "Subscription not found"

    doc = {k: v for k, v in result.items() if k != "_id"}
    doc["secret"] = mask_secret(doc.get("secret", ""))
    return doc, ""


async def delete_subscription(db, subscription_id: str, organization_id: str) -> bool:
    """Soft-delete a subscription (set inactive)."""
    result = await db.webhook_subscriptions.update_one(
        {"subscription_id": subscription_id, "organization_id": organization_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return result.modified_count > 0


async def rotate_secret(db, subscription_id: str, organization_id: str) -> tuple[Optional[str], str]:
    """Rotate the webhook secret. Returns (new_plain_secret, error)."""
    new_secret = generate_secret()
    now = datetime.now(timezone.utc).isoformat()

    result = await db.webhook_subscriptions.update_one(
        {"subscription_id": subscription_id, "organization_id": organization_id, "is_active": True},
        {"$set": {"secret": new_secret, "updated_at": now}},
    )
    if result.modified_count == 0:
        return None, "Subscription not found or inactive"
    return new_secret, ""


# ── Delivery Operations ──────────────────────────────────────

async def create_delivery(
    db,
    subscription_id: str,
    organization_id: str,
    event_id: str,
    event_type: str,
) -> tuple[Optional[dict], str]:
    """Create a delivery record.

    Idempotency: subscription_id + event_id must be unique.
    Returns (delivery_doc, error).
    """
    delivery_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    doc = {
        "delivery_id": delivery_id,
        "subscription_id": subscription_id,
        "organization_id": organization_id,
        "event_id": event_id,
        "event_type": event_type,
        "attempt_number": 0,
        "status": "pending",
        "response_status_code": None,
        "response_time_ms": None,
        "next_retry_at": now.isoformat(),
        "last_error": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    from pymongo.errors import DuplicateKeyError
    try:
        await db.webhook_deliveries.insert_one(doc)
    except DuplicateKeyError:
        return None, "Delivery already exists for this subscription + event"

    result = {k: v for k, v in doc.items() if k != "_id"}
    return result, ""


async def record_delivery_attempt(
    db,
    delivery_id: str,
    attempt_number: int,
    status: str,
    response_status_code: Optional[int] = None,
    response_time_ms: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    """Record a delivery attempt result and schedule retry if needed."""
    now = datetime.now(timezone.utc)

    update: dict[str, Any] = {
        "status": status,
        "attempt_number": attempt_number,
        "response_status_code": response_status_code,
        "response_time_ms": response_time_ms,
        "last_error": error,
        "updated_at": now.isoformat(),
    }

    # If failed and retries remain, schedule next retry
    if status == "retrying" and attempt_number < MAX_RETRY_ATTEMPTS:
        delay = RETRY_DELAYS[min(attempt_number, len(RETRY_DELAYS) - 1)]
        next_retry = now + timedelta(seconds=delay)
        update["next_retry_at"] = next_retry.isoformat()
    elif status == "failed":
        update["next_retry_at"] = None

    await db.webhook_deliveries.update_one(
        {"delivery_id": delivery_id},
        {"$set": update},
    )

    # Log the attempt
    await db.webhook_delivery_attempts.insert_one({
        "delivery_id": delivery_id,
        "attempt_number": attempt_number,
        "status": status,
        "response_status_code": response_status_code,
        "response_time_ms": response_time_ms,
        "error": error,
        "attempted_at": now.isoformat(),
    })


def should_retry(status_code: Optional[int], error: Optional[str]) -> bool:
    """Determine if a failed delivery should be retried.

    Retry on: network errors, 5xx, 429 (rate limited)
    No retry on: 4xx (except 429)
    """
    if error and status_code is None:
        # Network error — retry
        return True
    if status_code is None:
        return True
    if status_code == 429:
        return True
    if status_code >= 500:
        return True
    # 4xx — do not retry
    return False


# ── Circuit Breaker for Webhook Endpoints ────────────────────

async def update_circuit_state(
    db,
    subscription_id: str,
    success: bool,
) -> None:
    """Update per-subscription circuit breaker state.

    After 5 consecutive failures → pause (circuit open)
    After 1 success in half-open → close circuit
    """
    sub = await db.webhook_subscriptions.find_one(
        {"subscription_id": subscription_id},
        {"circuit_state": 1, "consecutive_failures": 1},
    )
    if not sub:
        return

    state = sub.get("circuit_state", "closed")
    failures = sub.get("consecutive_failures", 0)

    if success:
        await db.webhook_subscriptions.update_one(
            {"subscription_id": subscription_id},
            {"$set": {
                "circuit_state": "closed",
                "consecutive_failures": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
    else:
        new_failures = failures + 1
        new_state = "open" if new_failures >= 5 else state
        await db.webhook_subscriptions.update_one(
            {"subscription_id": subscription_id},
            {"$set": {
                "circuit_state": new_state,
                "consecutive_failures": new_failures,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )


async def is_circuit_open(db, subscription_id: str) -> bool:
    """Check if circuit breaker is open for a subscription."""
    sub = await db.webhook_subscriptions.find_one(
        {"subscription_id": subscription_id},
        {"circuit_state": 1, "consecutive_failures": 1, "updated_at": 1},
    )
    if not sub:
        return True  # No subscription = don't deliver

    state = sub.get("circuit_state", "closed")
    if state != "open":
        return False

    # Auto-recovery: if open for > 30 min, move to half_open
    updated = sub.get("updated_at", "")
    if updated:
        try:
            last_update = datetime.fromisoformat(updated) if isinstance(updated, str) else updated
            if datetime.now(timezone.utc) - last_update > timedelta(minutes=30):
                await db.webhook_subscriptions.update_one(
                    {"subscription_id": subscription_id},
                    {"$set": {"circuit_state": "half_open"}},
                )
                return False
        except Exception:
            pass

    return True


# ── Index Setup ──────────────────────────────────────────────

async def ensure_webhook_indexes(db) -> None:
    """Create MongoDB indexes for webhook collections."""
    # Subscription indexes
    await db.webhook_subscriptions.create_index(
        [("subscription_id", 1)], unique=True
    )
    await db.webhook_subscriptions.create_index(
        [("organization_id", 1), ("is_active", 1)]
    )
    await db.webhook_subscriptions.create_index(
        [("organization_id", 1), ("target_url", 1), ("subscribed_events", 1)],
    )

    # Delivery indexes — idempotency
    await db.webhook_deliveries.create_index(
        [("subscription_id", 1), ("event_id", 1)], unique=True
    )
    await db.webhook_deliveries.create_index(
        [("organization_id", 1), ("status", 1)]
    )
    await db.webhook_deliveries.create_index(
        [("status", 1), ("next_retry_at", 1)]
    )
    await db.webhook_deliveries.create_index(
        [("subscription_id", 1), ("created_at", -1)]
    )
    await db.webhook_deliveries.create_index(
        [("event_type", 1), ("status", 1)]
    )

    # Delivery attempts index
    await db.webhook_delivery_attempts.create_index(
        [("delivery_id", 1), ("attempt_number", 1)]
    )

    logger.info("Webhook indexes ensured")
