"""Enterprise Governance — Data Access Policy Service (Part 7).

Implements data access rules. Example: agency users cannot view other agencies' data.
Policy-based access control with configurable rules per organization.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.domain.governance.models import DATA_ACCESS_RESOURCES, POLICY_EFFECT_ALLOW, POLICY_EFFECT_DENY

logger = logging.getLogger("governance.data_access")


async def create_data_access_policy(
    db: Any,
    org_id: str,
    *,
    name: str,
    description: str,
    resource: str,
    effect: str,
    conditions: dict,
    applies_to_roles: list[str],
    actor_email: str,
) -> dict:
    """Create a data access policy rule."""
    now = datetime.now(timezone.utc)
    doc = {
        "_id": str(uuid.uuid4()),
        "organization_id": org_id,
        "name": name,
        "description": description,
        "resource": resource,
        "effect": effect,  # "allow" or "deny"
        "conditions": conditions,
        "applies_to_roles": applies_to_roles,
        "is_active": True,
        "priority": 100,
        "created_at": now,
        "created_by": actor_email,
        "updated_at": now,
    }
    await db.gov_data_policies.insert_one(doc)
    return {
        "policy_id": doc["_id"],
        "name": name,
        "resource": resource,
        "effect": effect,
        "timestamp": now.isoformat(),
    }


async def list_data_access_policies(
    db: Any, org_id: str, resource: Optional[str] = None,
) -> list[dict]:
    """List all data access policies."""
    query: dict[str, Any] = {"organization_id": org_id, "is_active": True}
    if resource:
        query["resource"] = resource
    docs = await db.gov_data_policies.find(
        query, {"_id": 0}
    ).sort("priority", -1).to_list(200)
    return docs


async def evaluate_data_access(
    db: Any,
    org_id: str,
    *,
    user_roles: list[str],
    resource: str,
    action: str,
    context: Optional[dict] = None,
) -> dict:
    """Evaluate if a data access request is allowed by policies."""
    policies = await db.gov_data_policies.find(
        {"organization_id": org_id, "resource": resource, "is_active": True}
    ).sort("priority", -1).to_list(50)

    # Default: allow if no policies defined
    if not policies:
        return {
            "allowed": True,
            "reason": "no_policies_defined",
            "matching_policy": None,
        }

    for policy in policies:
        applies_to = policy.get("applies_to_roles", [])
        # Check if any user role matches
        if not any(r in applies_to for r in user_roles) and "*" not in applies_to:
            continue

        # Evaluate conditions
        conditions = policy.get("conditions", {})
        conditions_met = _evaluate_conditions(conditions, context or {})

        if conditions_met:
            effect = policy.get("effect", POLICY_EFFECT_ALLOW)
            return {
                "allowed": effect == POLICY_EFFECT_ALLOW,
                "reason": f"policy:{policy.get('name', 'unnamed')}",
                "matching_policy": policy.get("name"),
                "effect": effect,
            }

    return {
        "allowed": True,
        "reason": "no_matching_policy",
        "matching_policy": None,
    }


async def update_data_access_policy(
    db: Any,
    org_id: str,
    policy_id: str,
    *,
    updates: dict,
    actor_email: str,
) -> dict:
    """Update a data access policy."""
    now = datetime.now(timezone.utc)
    updates["updated_at"] = now
    updates["updated_by"] = actor_email

    result = await db.gov_data_policies.update_one(
        {"_id": policy_id, "organization_id": org_id},
        {"$set": updates},
    )
    return {
        "policy_id": policy_id,
        "updated": result.modified_count > 0,
        "timestamp": now.isoformat(),
    }


async def delete_data_access_policy(
    db: Any, org_id: str, policy_id: str, actor_email: str,
) -> dict:
    """Soft-delete a data access policy."""
    now = datetime.now(timezone.utc)
    result = await db.gov_data_policies.update_one(
        {"_id": policy_id, "organization_id": org_id},
        {"$set": {"is_active": False, "deleted_at": now, "deleted_by": actor_email}},
    )
    return {
        "policy_id": policy_id,
        "deleted": result.modified_count > 0,
        "timestamp": now.isoformat(),
    }


async def seed_default_policies(db: Any, org_id: str, actor_email: str) -> dict:
    """Seed default data access policies for common scenarios."""
    now = datetime.now(timezone.utc)
    default_policies = [
        {
            "name": "agency_data_isolation",
            "description": "Agency users cannot view other agencies' data",
            "resource": "agencies",
            "effect": POLICY_EFFECT_DENY,
            "conditions": {"cross_org_access": True},
            "applies_to_roles": ["agency_admin", "agent", "support"],
        },
        {
            "name": "finance_data_restriction",
            "description": "Only finance admins can access financial settlements",
            "resource": "settlements",
            "effect": POLICY_EFFECT_DENY,
            "conditions": {"role_not_in": ["super_admin", "finance_admin"]},
            "applies_to_roles": ["agent", "support"],
        },
        {
            "name": "audit_log_read_only",
            "description": "Audit logs are read-only for non-governance roles",
            "resource": "audit_logs",
            "effect": POLICY_EFFECT_DENY,
            "conditions": {"action": "write"},
            "applies_to_roles": ["*"],
        },
        {
            "name": "customer_pii_protection",
            "description": "Support can view but not export customer PII",
            "resource": "customers",
            "effect": POLICY_EFFECT_DENY,
            "conditions": {"action": "export"},
            "applies_to_roles": ["support"],
        },
    ]

    seeded = 0
    for policy in default_policies:
        existing = await db.gov_data_policies.find_one(
            {"name": policy["name"], "organization_id": org_id}
        )
        if not existing:
            await db.gov_data_policies.insert_one({
                "_id": str(uuid.uuid4()),
                "organization_id": org_id,
                **policy,
                "is_active": True,
                "priority": 100,
                "created_at": now,
                "created_by": actor_email,
                "updated_at": now,
            })
            seeded += 1

    return {"policies_seeded": seeded, "timestamp": now.isoformat()}


def _evaluate_conditions(conditions: dict, context: dict) -> bool:
    """Evaluate policy conditions against request context."""
    if not conditions:
        return True

    for key, expected in conditions.items():
        actual = context.get(key)
        if key == "cross_org_access":
            # True if requesting org != target org
            if expected and context.get("requesting_org_id") != context.get("target_org_id"):
                return True
        elif key == "role_not_in":
            user_roles = context.get("user_roles", [])
            if not any(r in expected for r in user_roles):
                return True
        elif key == "action":
            if actual == expected:
                return True
        elif actual != expected:
            return False

    return False
