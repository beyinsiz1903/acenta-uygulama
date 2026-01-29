from __future__ import annotations

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.org_repository import OrgRepository
from app.repositories.credit_profile_repository import CreditProfileRepository
from app.repositories.refund_policy_repository import RefundPolicyRepository
from app.repositories.risk_rule_repository import RiskRuleRepository
from app.repositories.task_queue_repository import TaskQueueRepository
from app.utils import now_utc
from app.services.audit import write_audit_log


STANDARD_CREDIT_LIMIT = 100000.0
STANDARD_SOFT_LIMIT_PCT = 0.8


async def create_org(db: AsyncIOMotorDatabase, payload: Dict[str, Any], actor_user: Dict[str, Any]) -> str:
    """Create a new organization and initialize default-mode records.

    This is the SINGLE entrypoint for org creation in Phase 1.
    """

    now = now_utc()
    org_repo = OrgRepository(db)
    org_doc: Dict[str, Any] = {
        "name": payload.get("name") or "New Organization",
        "slug": payload.get("slug") or payload.get("name", "").lower().replace(" ", "-") or None,
        "created_at": now,
        "updated_at": now,
        "settings": payload.get("settings") or {"currency": "TRY"},
    }

    org_id = await org_repo.create_org(org_doc)

    # Audit: ORG_CREATED
    await _write_audit_system_event(
        db,
        organization_id=org_id,
        actor_user=actor_user,
        action="ORG_CREATED",
        target_type="org",
        target_id=org_id,
        meta={"name": org_doc["name"], "slug": org_doc.get("slug")},
    )

    try:
        await initialize_org_defaults(db, org_id, actor_user)
    except Exception:
        # Best-effort rollback: delete org + any seeded docs
        await _rollback_org_creation(db, org_id)
        raise

    return org_id


async def initialize_org_defaults(db: AsyncIOMotorDatabase, org_id: str, actor_user: Dict[str, Any]) -> None:
    """Ensure default-mode records exist for given org.

    Idempotent: calling this multiple times must not create duplicates.
    """

    await _ensure_credit_profile(db, org_id, actor_user)
    await _ensure_refund_policy(db, org_id, actor_user)
    await _ensure_risk_rules(db, org_id, actor_user)
    await _ensure_task_queues(db, org_id, actor_user)

    # Audit: ORG_INITIALIZED + DEFAULTS_CREATED
    await _write_audit_system_event(
        db,
        organization_id=org_id,
        actor_user=actor_user,
        action="ORG_INITIALIZED",
        target_type="org",
        target_id=org_id,
        meta={},
    )
    await _write_audit_system_event(
        db,
        organization_id=org_id,
        actor_user=actor_user,
        action="DEFAULTS_CREATED",
        target_type="org_defaults",
        target_id=org_id,
        meta={
            "credit_profile": "Standard",
            "refund_policy": True,
            "risk_rules": ["high_amount", "burst_bookings", "high_refund_ratio"],
            "task_queues": ["Ops", "Finance"],
        },
    )


async def _rollback_org_creation(db: AsyncIOMotorDatabase, org_id: str) -> None:
    """Best-effort rollback of org and its default-mode records.

    Used when seeding fails and transactions are not available.
    """

    org_repo = OrgRepository(db)
    await org_repo.delete_org(org_id)

    credit_repo = CreditProfileRepository(db)
    await credit_repo.delete_for_org(org_id)

    refund_repo = RefundPolicyRepository(db)
    await refund_repo.delete_for_org(org_id)

    risk_repo = RiskRuleRepository(db)
    await risk_repo.delete_for_org(org_id)

    queue_repo = TaskQueueRepository(db)
    await queue_repo.delete_for_org(org_id)


async def _ensure_credit_profile(db: AsyncIOMotorDatabase, org_id: str, actor_user: Dict[str, Any]) -> None:
    repo = CreditProfileRepository(db)
    await repo.ensure_standard_profile(org_id, actor_user.get("email"))


async def _ensure_refund_policy(db: AsyncIOMotorDatabase, org_id: str, actor_user: Dict[str, Any]) -> None:
    repo = RefundPolicyRepository(db)
    await repo.ensure_default_policy(org_id, actor_user.get("email"))


async def _ensure_risk_rules(db: AsyncIOMotorDatabase, org_id: str, actor_user: Dict[str, Any]) -> None:
    repo = RiskRuleRepository(db)
    await repo.ensure_default_rules(org_id, actor_user.get("email"))


async def _ensure_task_queues(db: AsyncIOMotorDatabase, org_id: str, actor_user: Dict[str, Any]) -> None:
    now = now_utc()
    for name in ("Ops", "Finance"):
        existing = await db.task_queues.find_one({"organization_id": org_id, "name": name})
        if existing:
            continue
        doc = {
            "organization_id": org_id,
            "name": name,
            "created_at": now,
            "updated_at": now,
            "created_by": actor_user.get("email"),
            "updated_by": actor_user.get("email"),
        }
        await db.task_queues.insert_one(doc)


async def _write_audit_system_event(
    db: AsyncIOMotorDatabase,
    *,
    organization_id: str,
    actor_user: Dict[str, Any],
    action: str,
    target_type: str,
    target_id: str,
    meta: Dict[str, Any] | None = None,
) -> None:
    """Helper to write org-scoped audit events without an HTTP Request.

    Uses a synthetic request-like object with minimal fields so that the
    existing write_audit_log() signature can be reused.
    """

    class _FakeRequest:
        def __init__(self) -> None:
            self.headers = {}
            self.client = None
            self.method = "SYSTEM"

            class _URL:
                def __init__(self) -> None:
                    self.path = "/system/org_init"

            self.url = _URL()

    actor = {
        "actor_type": "user",
        "actor_id": actor_user.get("id") or actor_user.get("email"),
        "email": actor_user.get("email"),
        "roles": actor_user.get("roles") or [],
    }

    await write_audit_log(
        db,
        organization_id=organization_id,
        actor=actor,
        request=_FakeRequest(),
        action=action,
        target_type=target_type,
        target_id=target_id,
        before=None,
        after=None,
        meta=meta or {},
    )
