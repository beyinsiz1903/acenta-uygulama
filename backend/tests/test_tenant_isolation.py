"""Cross-tenant isolation tests — negative scenarios.

These tests verify that tenant boundaries are enforced:
- Tenant A cannot read Tenant B's data
- Tenant A cannot update Tenant B's data
- Aggregate queries stay within tenant scope
- Missing tenant context causes hard errors
- TenantScopedRepository enforces isolation

Run: pytest /app/backend/tests/test_tenant_isolation.py -v
"""
from __future__ import annotations

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.modules.tenant.context import TenantContext
from app.modules.tenant.repository import TenantScopedRepository
from app.modules.tenant.errors import (
    TenantContextMissing,
    TenantFilterBypassAttempt,
)
from app.modules.tenant.admin_bypass import (
    is_collection_tenant_scoped,
    is_collection_global,
    is_path_tenant_exempt,
    TENANT_SCOPED_COLLECTIONS,
    GLOBAL_COLLECTIONS,
)
from app.modules.tenant.guard import validate_query_has_tenant_filter
from app.repositories.base_repository import with_org_filter, with_tenant_filter


# ============================================================================
# Fixtures
# ============================================================================

TENANT_A = TenantContext(org_id="org_alpha", tenant_id="t_alpha", user_id="user_1")
TENANT_B = TenantContext(org_id="org_beta", tenant_id="t_beta", user_id="user_2")
SUPER_ADMIN = TenantContext(org_id="org_alpha", tenant_id="t_alpha", user_id="admin_1", is_super_admin=True)
NO_ORG = TenantContext(org_id="", tenant_id="", user_id="orphan_1")


class TestBookingRepo(TenantScopedRepository):
    collection_name = "bookings"


class TestPaymentRepo(TenantScopedRepository):
    collection_name = "payments"


def _mock_db():
    """Create a mock Motor database."""
    db = MagicMock()
    mock_col = MagicMock()
    mock_col.find_one = AsyncMock(return_value=None)
    mock_col.find = MagicMock()
    mock_col.find.return_value.sort = MagicMock()
    mock_col.find.return_value.sort.return_value.limit = MagicMock()
    mock_col.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
    mock_col.find.return_value.limit = MagicMock()
    mock_col.find.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
    mock_col.count_documents = AsyncMock(return_value=0)
    mock_col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="new_id"))
    mock_col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock_col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    mock_col.aggregate = MagicMock()
    mock_col.aggregate.return_value.to_list = AsyncMock(return_value=[])
    db.__getitem__ = MagicMock(return_value=mock_col)
    return db, mock_col


# ============================================================================
# Test: TenantContext
# ============================================================================

class TestTenantContext:
    def test_org_filter(self):
        assert TENANT_A.org_filter == {"organization_id": "org_alpha"}

    def test_scoped_filter_simple(self):
        result = TENANT_A.scoped_filter({"status": "confirmed"})
        assert result == {"organization_id": "org_alpha", "status": "confirmed"}

    def test_scoped_filter_no_extra(self):
        result = TENANT_A.scoped_filter()
        assert result == {"organization_id": "org_alpha"}


# ============================================================================
# Test: TenantScopedRepository — Isolation enforcement
# ============================================================================

class TestTenantScopedRepository:
    def test_scoped_injects_org_id(self):
        db, _ = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        result = repo._scoped({"status": "draft"})
        assert result["organization_id"] == "org_alpha"
        assert result["status"] == "draft"

    def test_scoped_rejects_empty_org(self):
        db, _ = _mock_db()
        repo = TestBookingRepo(db, NO_ORG)
        with pytest.raises(TenantContextMissing):
            repo._scoped({"status": "draft"})

    def test_scoped_rejects_cross_tenant_org_override(self):
        db, _ = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        with pytest.raises(TenantFilterBypassAttempt):
            repo._scoped({"organization_id": "org_beta", "status": "draft"})

    def test_scoped_allows_matching_org(self):
        db, _ = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        result = repo._scoped({"organization_id": "org_alpha", "status": "draft"})
        assert result["organization_id"] == "org_alpha"

    def test_scope_pipeline_injects_match(self):
        db, _ = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        result = repo._scope_pipeline(pipeline)
        assert result[0] == {"$match": {"organization_id": "org_alpha"}}
        assert result[1] == {"$group": {"_id": "$status", "count": {"$sum": 1}}}

    def test_scope_pipeline_merges_existing_match(self):
        db, _ = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        pipeline = [
            {"$match": {"status": "confirmed"}},
            {"$group": {"_id": "$hotel_id"}},
        ]
        result = repo._scope_pipeline(pipeline)
        assert result[0] == {"$match": {"status": "confirmed", "organization_id": "org_alpha"}}

    def test_scope_pipeline_rejects_cross_tenant(self):
        db, _ = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        pipeline = [{"$match": {"organization_id": "org_beta"}}]
        with pytest.raises(TenantFilterBypassAttempt):
            repo._scope_pipeline(pipeline)

    def test_scope_pipeline_empty(self):
        db, _ = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        result = repo._scope_pipeline([])
        assert result == [{"$match": {"organization_id": "org_alpha"}}]

    @pytest.mark.anyio
    async def test_find_one_includes_org_filter(self):
        db, mock_col = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        await repo.find_one({"status": "confirmed"})
        mock_col.find_one.assert_called_once_with(
            {"status": "confirmed", "organization_id": "org_alpha"},
            None,
        )

    @pytest.mark.anyio
    async def test_insert_stamps_org_id(self):
        db, mock_col = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        doc = {"status": "draft", "amount": 100}
        await repo.insert_one(doc)
        inserted = mock_col.insert_one.call_args[0][0]
        assert inserted["organization_id"] == "org_alpha"

    @pytest.mark.anyio
    async def test_insert_with_no_org_fails(self):
        db, _ = _mock_db()
        repo = TestBookingRepo(db, NO_ORG)
        with pytest.raises(TenantContextMissing):
            await repo.insert_one({"status": "draft"})

    @pytest.mark.anyio
    async def test_update_one_scoped(self):
        db, mock_col = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        await repo.update_one({"status": "draft"}, {"$set": {"status": "confirmed"}})
        call_args = mock_col.update_one.call_args
        assert call_args[0][0]["organization_id"] == "org_alpha"

    @pytest.mark.anyio
    async def test_delete_one_scoped(self):
        db, mock_col = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        await repo.delete_one({"status": "cancelled"})
        call_args = mock_col.delete_one.call_args
        assert call_args[0][0]["organization_id"] == "org_alpha"

    @pytest.mark.anyio
    async def test_count_scoped(self):
        db, mock_col = _mock_db()
        repo = TestBookingRepo(db, TENANT_A)
        await repo.count({"status": "confirmed"})
        call_args = mock_col.count_documents.call_args
        assert call_args[0][0]["organization_id"] == "org_alpha"


# ============================================================================
# Test: Cross-tenant access prevention
# ============================================================================

class TestCrossTenantPrevention:
    def test_tenant_a_cannot_query_tenant_b(self):
        """CRITICAL: Tenant A repo cannot be used to query Tenant B data."""
        db, _ = _mock_db()
        repo_a = TestBookingRepo(db, TENANT_A)
        with pytest.raises(TenantFilterBypassAttempt):
            repo_a._scoped({"organization_id": "org_beta"})

    def test_tenant_b_cannot_query_tenant_a(self):
        db, _ = _mock_db()
        repo_b = TestBookingRepo(db, TENANT_B)
        with pytest.raises(TenantFilterBypassAttempt):
            repo_b._scoped({"organization_id": "org_alpha"})

    def test_aggregate_cross_tenant_blocked(self):
        db, _ = _mock_db()
        repo_a = TestBookingRepo(db, TENANT_A)
        with pytest.raises(TenantFilterBypassAttempt):
            repo_a._scope_pipeline([
                {"$match": {"organization_id": "org_beta"}},
                {"$group": {"_id": "$status"}},
            ])

    def test_with_org_filter_rejects_mismatch(self):
        with pytest.raises(ValueError, match="Cross-tenant access attempt"):
            with_org_filter({"organization_id": "org_X"}, "org_Y")


# ============================================================================
# Test: Admin bypass rules
# ============================================================================

class TestAdminBypass:
    def test_bookings_is_tenant_scoped(self):
        assert is_collection_tenant_scoped("bookings")

    def test_payments_is_tenant_scoped(self):
        assert is_collection_tenant_scoped("payments")

    def test_organizations_is_global(self):
        assert is_collection_global("organizations")

    def test_tenants_is_global(self):
        assert is_collection_global("tenants")

    def test_unknown_collection_not_scoped(self):
        assert not is_collection_tenant_scoped("random_stuff")

    def test_health_path_exempt(self):
        assert is_path_tenant_exempt("/api/healthz")

    def test_login_path_exempt(self):
        assert is_path_tenant_exempt("/api/auth/login")

    def test_public_prefix_exempt(self):
        assert is_path_tenant_exempt("/api/public/search")

    def test_bookings_path_not_exempt(self):
        assert not is_path_tenant_exempt("/api/bookings")


# ============================================================================
# Test: with_org_filter hardening
# ============================================================================

class TestWithOrgFilter:
    def test_injects_org_id(self):
        result = with_org_filter({"status": "active"}, "org_1")
        assert result == {"status": "active", "organization_id": "org_1"}

    def test_rejects_empty_org(self):
        with pytest.raises(ValueError):
            with_org_filter({"status": "active"}, "")

    def test_rejects_cross_tenant_override(self):
        with pytest.raises(ValueError, match="Cross-tenant access attempt"):
            with_org_filter({"organization_id": "org_other"}, "org_mine")

    def test_allows_same_org(self):
        result = with_org_filter({"organization_id": "org_1"}, "org_1")
        assert result["organization_id"] == "org_1"


# ============================================================================
# Test: with_tenant_filter hardening
# ============================================================================

class TestWithTenantFilter:
    def test_strict_mode_no_legacy(self):
        result = with_tenant_filter({"status": "active"}, "t_1")
        # With include_legacy_without_tenant=False (new default)
        assert result == {"$and": [{"status": "active"}, {"tenant_id": "t_1"}]}

    def test_rejects_empty_tenant(self):
        with pytest.raises(ValueError):
            with_tenant_filter({"status": "active"}, "")

    def test_legacy_mode_deprecated(self):
        """Legacy mode should still work but with deprecation warning."""
        result = with_tenant_filter(
            {"status": "active"}, "t_1",
            include_legacy_without_tenant=True,
        )
        # Should have $or clause
        assert "$and" in result
        inner = result["$and"][1]
        assert "$or" in inner


# ============================================================================
# Test: Query validation guard
# ============================================================================

class TestQueryValidation:
    def test_valid_scoped_query(self):
        assert validate_query_has_tenant_filter(
            "bookings",
            {"organization_id": "org_1", "status": "confirmed"},
        ) is True

    def test_unscoped_query_on_tenant_collection(self):
        assert validate_query_has_tenant_filter(
            "bookings",
            {"status": "confirmed"},
        ) is False

    def test_global_collection_no_filter_needed(self):
        assert validate_query_has_tenant_filter(
            "organizations",
            {"name": "test"},
        ) is True

    def test_and_clause_with_org(self):
        assert validate_query_has_tenant_filter(
            "payments",
            {"$and": [{"organization_id": "org_1"}, {"amount": {"$gt": 0}}]},
        ) is True
