from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.auth import hash_password
from app.db import get_db
from app.errors import AppError
from app.constants.plan_matrix import PLAN_MATRIX, DEFAULT_PLAN, VALID_PLANS
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

TRIAL_DAYS = 14


class OnboardingService:
    """Self-service SaaS onboarding – 2-step signup + wizard."""

    # ─── STEP A: Atomic org + tenant + user ────────────────────────
    async def signup_step_a(
        self,
        *,
        company_name: str,
        admin_name: str,
        email: str,
        password: str,
    ) -> Dict[str, Any]:
        """Create org, tenant, admin user.  Returns created IDs.
        Rolls back on any failure."""
        db = await get_db()
        now = datetime.now(timezone.utc)

        # Duplicate email check
        existing = await db.users.find_one({"email": email})
        if existing:
            raise AppError(409, "email_exists", "Bu e-posta adresi zaten kayıtlı.", {"email": email})

        org_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        slug = company_name.lower().replace(" ", "-").replace(".", "")[:40] + "-" + uuid.uuid4().hex[:6]

        try:
            # 1) Organization
            org_doc = {
                "_id": org_id,
                "name": company_name,
                "slug": slug,
                "settings": {"currency": "TRY"},
                "created_at": now,
                "updated_at": now,
            }
            await db.organizations.insert_one(org_doc)

            # 2) Tenant
            tenant_doc = {
                "_id": tenant_id,
                "organization_id": org_id,
                "name": company_name,
                "tenant_key": slug,
                "status": "active",
                "is_active": True,
                "onboarding_completed": False,
                "created_at": now,
                "updated_at": now,
            }
            await db.tenants.insert_one(tenant_doc)

            # 3) Admin user
            user_doc = {
                "_id": user_id,
                "email": email,
                "name": admin_name,
                "password_hash": hash_password(password),
                "roles": ["super_admin"],
                "organization_id": org_id,
                "tenant_id": tenant_id,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            await db.users.insert_one(user_doc)

        except AppError:
            raise
        except Exception as exc:
            # Rollback - use delete_many to handle partial inserts
            try:
                await db.users.delete_one({"_id": user_id})
            except Exception:
                pass
            try:
                await db.tenants.delete_one({"_id": tenant_id})
            except Exception:
                pass
            try:
                await db.organizations.delete_one({"_id": org_id})
            except Exception:
                pass
            logger.error("signup_step_a rollback: %s", exc)
            raise AppError(500, "signup_failed", "Kayıt oluşturulamadı.", {})

        return {"org_id": org_id, "tenant_id": tenant_id, "user_id": user_id}

    # ─── STEP B: Trial + capabilities + onboarding state ─────────
    async def signup_step_b(
        self,
        *,
        org_id: str,
        tenant_id: str,
        user_id: str,
        plan: str = DEFAULT_PLAN,
        billing_cycle: str = "monthly",
    ) -> Dict[str, Any]:
        """Seed trial subscription, capabilities, onboarding_state."""
        db = await get_db()
        now = datetime.now(timezone.utc)
        trial_end = now + timedelta(days=TRIAL_DAYS)

        plan_key = plan if plan in VALID_PLANS else DEFAULT_PLAN

        # 1) Trial subscription (no Stripe dependency)
        sub_id = str(uuid.uuid4())
        sub_doc = {
            "_id": sub_id,
            "org_id": org_id,
            "tenant_id": tenant_id,
            "plan": plan_key,
            "status": "trialing",
            "billing_cycle": billing_cycle,
            "billing_enabled": False,
            "trial_start": now,
            "trial_end": trial_end,
            "period_start": now,
            "period_end": trial_end,
            "created_at": now,
            "updated_at": now,
        }
        await db.subscriptions.insert_one(sub_doc)

        # 2) Tenant capabilities (plan features)
        cap_set = {
            "tenant_id": tenant_id,
            "plan": plan_key,
            "add_ons": [],
            "updated_at": now,
        }
        await db.tenant_capabilities.update_one(
            {"tenant_id": tenant_id},
            {"$set": cap_set, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )

        # 3) Onboarding state
        onboarding_doc = {
            "_id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "org_id": org_id,
            "user_id": user_id,
            "steps": {
                "company": False,
                "product": False,
                "invite": False,
                "partner": False,
            },
            "completed_at": None,
            "created_at": now,
            "updated_at": now,
        }
        await db.onboarding_state.insert_one(onboarding_doc)

        return {
            "subscription_id": sub_id,
            "plan": plan_key,
            "trial_end": trial_end.isoformat(),
        }

    # ─── Full signup (combines A + B) ─────────────────────────────
    async def signup(
        self,
        *,
        company_name: str,
        admin_name: str,
        email: str,
        password: str,
        plan: str = DEFAULT_PLAN,
        billing_cycle: str = "monthly",
    ) -> Dict[str, Any]:
        step_a = await self.signup_step_a(
            company_name=company_name,
            admin_name=admin_name,
            email=email,
            password=password,
        )
        step_b = await self.signup_step_b(
            org_id=step_a["org_id"],
            tenant_id=step_a["tenant_id"],
            user_id=step_a["user_id"],
            plan=plan,
            billing_cycle=billing_cycle,
        )
        return {**step_a, **step_b}

    # ─── Onboarding state CRUD ────────────────────────────────────
    async def get_state(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        db = await get_db()
        doc = await db.onboarding_state.find_one({"tenant_id": tenant_id})
        if doc:
            doc["id"] = str(doc.pop("_id", ""))
        return doc

    async def update_step(self, tenant_id: str, step: str, data: Dict[str, Any]) -> Dict[str, Any]:
        db = await get_db()
        now = datetime.now(timezone.utc)
        valid_steps = ["company", "product", "invite", "partner"]
        if step not in valid_steps:
            raise AppError(400, "invalid_step", f"Geçersiz adım: {step}", {"step": step})

        state = await db.onboarding_state.find_one({"tenant_id": tenant_id})
        if not state:
            raise AppError(404, "onboarding_not_found", "Onboarding durumu bulunamadı.", {})

        update_fields = {
            f"steps.{step}": True,
            "updated_at": now,
        }
        if data:
            update_fields[f"step_data.{step}"] = data

        await db.onboarding_state.update_one(
            {"tenant_id": tenant_id},
            {"$set": update_fields},
        )
        return await self.get_state(tenant_id)

    async def complete_onboarding(self, tenant_id: str) -> Dict[str, Any]:
        db = await get_db()
        now = datetime.now(timezone.utc)

        await db.onboarding_state.update_one(
            {"tenant_id": tenant_id},
            {"$set": {"completed_at": now, "updated_at": now}},
        )
        await db.tenants.update_one(
            {"_id": tenant_id},
            {"$set": {"onboarding_completed": True, "updated_at": now}},
        )
        return await self.get_state(tenant_id)

    # ─── Trial expiration check ───────────────────────────────────
    async def check_trial_status(self, org_id: str) -> Dict[str, Any]:
        db = await get_db()
        sub = await db.subscriptions.find_one(
            {"org_id": org_id, "status": "trialing"},
            sort=[("period_end", -1)],
        )
        if not sub:
            return {"status": "no_trial", "expired": True}

        now = datetime.now(timezone.utc)
        trial_end = sub.get("trial_end") or sub.get("period_end")
        if trial_end and now > trial_end:
            # Auto-expire
            await db.subscriptions.update_one(
                {"_id": sub["_id"]},
                {"$set": {"status": "expired", "updated_at": now}},
            )
            return {"status": "expired", "expired": True, "trial_end": trial_end.isoformat()}

        days_remaining = (trial_end - now).days if trial_end else 0
        return {
            "status": "trialing",
            "expired": False,
            "trial_end": trial_end.isoformat() if trial_end else None,
            "days_remaining": days_remaining,
        }


onboarding_service = OnboardingService()
