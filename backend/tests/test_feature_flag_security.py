"""
Test: LEGACY_ROLE_ALIASES Security Fix Verification

This test validates that:
1. admin role users DO NOT bypass feature flag checks (require_feature)
2. super_admin users DO bypass feature flag checks
3. require_roles still works with admin → super_admin aliasing for route access
4. agency_admin users do NOT bypass feature flag checks
"""
from __future__ import annotations

from datetime import datetime

import pytest

from app.auth import create_access_token, is_super_admin, normalize_roles


class TestIsSuperAdminFunction:
    """Unit tests for is_super_admin function behavior with _raw_roles"""

    def test_plain_admin_is_not_super_admin(self):
        """Plain 'admin' role should NOT be treated as super_admin for feature bypass"""
        user = {
            "roles": ["super_admin"],  # After normalization
            "_raw_roles": ["admin"],  # Original role before normalization
        }
        assert is_super_admin(user) is False

    def test_explicit_super_admin_is_super_admin(self):
        """Explicit 'super_admin' role SHOULD be treated as super_admin"""
        user = {
            "roles": ["super_admin"],
            "_raw_roles": ["super_admin"],
        }
        assert is_super_admin(user) is True

    def test_explicit_superadmin_is_super_admin(self):
        """Explicit 'superadmin' (no underscore) SHOULD be treated as super_admin"""
        user = {
            "roles": ["super_admin"],
            "_raw_roles": ["superadmin"],
        }
        assert is_super_admin(user) is True

    def test_agency_admin_is_not_super_admin(self):
        """agency_admin should NOT be treated as super_admin"""
        user = {
            "roles": ["agency_admin"],
            "_raw_roles": ["agency_admin"],
        }
        assert is_super_admin(user) is False

    def test_user_role_is_not_super_admin(self):
        """Regular 'user' role should NOT be super_admin"""
        user = {
            "roles": ["user"],
            "_raw_roles": ["user"],
        }
        assert is_super_admin(user) is False


class TestNormalizeRolesAliasing:
    """Verify that normalize_roles still aliases admin → super_admin"""

    def test_admin_normalizes_to_super_admin(self):
        """LEGACY_ROLE_ALIASES: 'admin' → 'super_admin' for route access"""
        result = normalize_roles(["admin"])
        assert result == ["super_admin"]

    def test_super_admin_stays_super_admin(self):
        """Explicit super_admin should stay as-is"""
        result = normalize_roles(["super_admin"])
        assert result == ["super_admin"]

    def test_agency_admin_stays_agency_admin(self):
        """agency_admin should NOT be aliased"""
        result = normalize_roles(["agency_admin"])
        assert result == ["agency_admin"]


# ============================================================================
# Integration Tests: Feature Flag Bypass Prevention
# ============================================================================

@pytest.mark.anyio
async def test_admin_without_b2b_pro_gets_404_settlements(async_client, test_db, anyio_backend):
    """
    SECURITY FIX VERIFICATION:
    User with roles=['admin'] and org without b2b_pro should get 404 from /api/admin/settlements
    """
    db = test_db

    org_id = "org_sec_test_no_b2b_pro_admin"
    await db.organizations.insert_one({
        "_id": org_id,
        "name": "Org Without B2B PRO",
        "features": {"b2b_pro": False}
    })

    email = "sec_test_admin_no_b2b@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin Without B2B PRO Access",
        "roles": ["admin"],  # Plain admin, NOT super_admin
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    resp = await async_client.get(
        "/api/admin/settlements",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Admin without b2b_pro should get 404 (feature disabled) - NOT 200
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text[:200]}"


@pytest.mark.anyio
async def test_admin_without_b2b_pro_gets_404_whitelabel(async_client, test_db, anyio_backend):
    """
    SECURITY FIX VERIFICATION:
    User with roles=['admin'] and org without b2b_pro should get 404 from /api/admin/whitelabel
    """
    db = test_db

    org_id = "org_sec_test_no_b2b_pro_whitelabel"
    await db.organizations.insert_one({
        "_id": org_id,
        "name": "Org Without B2B PRO",
        "features": {"b2b_pro": False}
    })

    email = "sec_test_admin_whitelabel_nopro@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin Without B2B PRO",
        "roles": ["admin"],  # Plain admin
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    resp = await async_client.get(
        "/api/admin/whitelabel",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Admin without b2b_pro should get 404
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text[:200]}"


@pytest.mark.anyio
async def test_super_admin_bypasses_feature_flag(async_client, test_db, anyio_backend):
    """
    SECURITY FIX VERIFICATION:
    User with roles=['super_admin'] should ALWAYS bypass feature checks and get 200
    """
    db = test_db

    org_id = "org_sec_test_super_admin_bypass"
    await db.organizations.insert_one({
        "_id": org_id,
        "name": "Org Without B2B PRO",
        "features": {"b2b_pro": False}  # Feature disabled
    })

    email = "sec_test_super_admin@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Super Admin",
        "roles": ["super_admin"],  # Explicit super_admin
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    # Super admin should bypass feature checks for settlements
    resp_settlements = await async_client.get(
        "/api/admin/settlements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_settlements.status_code == 200, f"Expected 200 for super_admin, got {resp_settlements.status_code}"

    # Super admin should bypass feature checks for whitelabel
    resp_whitelabel = await async_client.get(
        "/api/admin/whitelabel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_whitelabel.status_code == 200, f"Expected 200 for super_admin, got {resp_whitelabel.status_code}"


@pytest.mark.anyio
async def test_agency_admin_without_b2b_pro_gets_blocked(async_client, test_db, anyio_backend):
    """
    SECURITY FIX VERIFICATION:
    User with roles=['agency_admin'] and org without b2b_pro should get 403/404
    """
    db = test_db

    org_id = "org_sec_test_agency_admin_blocked"
    await db.organizations.insert_one({
        "_id": org_id,
        "name": "Org Without B2B PRO",
        "features": {"b2b_pro": False}
    })

    email = "sec_test_agency_admin@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Agency Admin",
        "roles": ["agency_admin"],
        "agency_id": "some_agency",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    resp = await async_client.get(
        "/api/admin/settlements",
        headers={"Authorization": f"Bearer {token}"},
    )
    # agency_admin without b2b_pro should be blocked
    assert resp.status_code in (403, 404), f"Expected 403/404, got {resp.status_code}"


@pytest.mark.anyio
async def test_admin_with_b2b_pro_enabled_gets_200_settlements(async_client, test_db, anyio_backend):
    """
    Admin user WITH b2b_pro enabled should get 200 from /api/admin/settlements
    """
    db = test_db

    org_id = "org_sec_test_admin_with_b2b_pro"
    await db.organizations.insert_one({
        "_id": org_id,
        "name": "Org With B2B PRO",
        "features": {"b2b_pro": True}  # Feature enabled
    })

    email = "sec_test_admin_with_b2b@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin With B2B PRO",
        "roles": ["admin"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    resp = await async_client.get(
        "/api/admin/settlements",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Admin with b2b_pro enabled should get 200
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"


@pytest.mark.anyio
async def test_admin_with_b2b_pro_enabled_gets_200_whitelabel(async_client, test_db, anyio_backend):
    """
    Admin user WITH b2b_pro enabled should get 200 from /api/admin/whitelabel
    """
    db = test_db

    org_id = "org_sec_test_admin_with_b2b_pro_wl"
    await db.organizations.insert_one({
        "_id": org_id,
        "name": "Org With B2B PRO",
        "features": {"b2b_pro": True}
    })

    email = "sec_test_admin_with_b2b_wl@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin With B2B PRO",
        "roles": ["admin"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    resp = await async_client.get(
        "/api/admin/whitelabel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"


@pytest.mark.anyio
async def test_require_roles_admin_can_access_super_admin_route(async_client, test_db, anyio_backend):
    """
    BACKWARD COMPATIBILITY:
    require_roles(['super_admin']) should still allow 'admin' users through
    (because normalize_roles aliases admin → super_admin for route matching)
    """
    db = test_db

    org_id = "org_sec_test_require_roles_compat"
    await db.organizations.insert_one({
        "_id": org_id,
        "name": "Test Org",
        "features": {"b2b_pro": True}  # Feature enabled
    })

    email = "sec_test_require_roles@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin User",
        "roles": ["admin"],  # Plain admin
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    # Settlements uses UserDep = require_roles(["super_admin", "admin", "agency_admin"])
    # Admin should have route access (due to normalization)
    resp = await async_client.get(
        "/api/admin/settlements",
        headers={"Authorization": f"Bearer {token}"},
    )
    # With b2b_pro=True, admin should get through both require_roles AND require_feature
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
