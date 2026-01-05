from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, validator

from app.auth import get_current_user, require_roles
from app.db import get_db

router = APIRouter(prefix="/api/admin/action-policies", tags=["admin-action-policies"])


class ActionRuleWhen(BaseModel):
    high_risk: bool = True
    reasons_any: List[str] = Field(default_factory=list)

    @validator("reasons_any", each_item=True)
    def _validate_reason(cls, v: str) -> str:
        if v not in {"rate", "repeat"}:
            raise ValueError("reasons_any can only contain 'rate' or 'repeat'")
        return v


class ActionRuleThen(BaseModel):
    action: str = Field("watchlist", description="none|watchlist|manual_review|block")
    requires_approval_to_unblock: bool = False
    notify_channels: List[str] = Field(default_factory=list)

    @validator("action")
    def _validate_action(cls, v: str) -> str:
        if v not in {"none", "watchlist", "manual_review", "block"}:
            raise ValueError("invalid action")
        return v

    @validator("notify_channels", each_item=True)
    def _validate_channel(cls, v: str) -> str:
        if v not in {"email", "webhook"}:
            raise ValueError("invalid notify channel")
        return v


class ActionRule(BaseModel):
    when: ActionRuleWhen
    then: ActionRuleThen


class MatchRiskActionPolicy(BaseModel):
    enabled: bool = True
    default_action: str = Field("watchlist", description="none|watchlist|manual_review|block")
    rules: List[ActionRule] = Field(default_factory=list)

    @validator("default_action")
    def _validate_default_action(cls, v: str) -> str:
        if v not in {"none", "watchlist", "manual_review", "block"}:
            raise ValueError("invalid default action")
        return v


class MatchRiskActionPolicyResponse(BaseModel):
    ok: bool = True
    policy: MatchRiskActionPolicy
    updated_at: Optional[str] = None
    updated_by_email: Optional[str] = None


async def _load_policy(db, org_id: str) -> dict[str, Any]:
    doc = await db.action_policies.find_one({"organization_id": org_id})
    if not doc:
        return {
            "organization_id": org_id,
            "enabled": True,
            "default_action": "watchlist",
            "rules": [],
            "updated_at": None,
            "updated_by_email": None,
        }
    return doc


@router.get(
    "/match-risk",
    response_model=MatchRiskActionPolicyResponse,
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def get_match_risk_action_policy(db=Depends(get_db), user=Depends(get_current_user)):
    org_id = user.get("organization_id")
    doc = await _load_policy(db, org_id)
    policy = MatchRiskActionPolicy(
        enabled=bool(doc.get("enabled", True)),
        default_action=str(doc.get("default_action", "watchlist")),
        rules=[ActionRule(**r) for r in doc.get("policy", {}).get("rules", [])]
        if doc.get("policy")
        else [ActionRule(**r) for r in doc.get("rules", [])]
    )
    updated_at = doc.get("updated_at")
    if hasattr(updated_at, "isoformat"):
        updated_at = updated_at.isoformat()
    return MatchRiskActionPolicyResponse(
        ok=True,
        policy=policy,
        updated_at=updated_at,
        updated_by_email=doc.get("updated_by_email"),
    )


@router.put(
    "/match-risk",
    response_model=MatchRiskActionPolicyResponse,
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def update_match_risk_action_policy(
    payload: MatchRiskActionPolicy, db=Depends(get_db), user=Depends(get_current_user)
):
    from app.utils import now_utc

    org_id = user.get("organization_id")
    now = now_utc()

    # store under a single 'policy' field to allow future versions
    doc = {
        "organization_id": org_id,
        "policy": payload.model_dump(),
        "enabled": payload.enabled,
        "default_action": payload.default_action,
        "updated_at": now,
        "updated_by_email": user.get("email"),
    }

    await db.action_policies.update_one(
        {"organization_id": org_id},
        {"$set": doc},
        upsert=True,
    )

    updated_at = now.isoformat()
    return MatchRiskActionPolicyResponse(
        ok=True,
        policy=payload,
        updated_at=updated_at,
        updated_by_email=user.get("email"),
    )
