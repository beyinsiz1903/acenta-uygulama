from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.auth import create_access_token
from app.db import get_db
from app.repositories.membership_repository import MembershipRepository
from app.services.feature_service import feature_service


@pytest.fixture
async def tenant_for_feature_test(test_db) -> dict:
  """Create a tenant tied to the default org for feature guard tests."""
  org = await test_db.organizations.find_one({"slug": "default"})
  assert org is not None, "default org must exist"

  doc = {
    "_id": ObjectId(),
    "organization_id": str(org["_id"]),
    "name": "Feature Test Tenant",
    "slug": "feature-test-tenant",
    "status": "active",
    "is_active": True,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
  }
  await test_db.tenants.insert_one(doc)
  return doc


@pytest.fixture
async def feature_test_user(test_db) -> dict:
  """Create a user with agency_admin role for feature guard tests."""
  org = await test_db.organizations.find_one({"slug": "default"})
  assert org is not None

  from app.auth import hash_password

  doc = {
    "_id": ObjectId(),
    "organization_id": str(org["_id"]),
    "email": "feature-test@test.local",
    "name": "Feature Test User",
    "password_hash": hash_password("test123"),
    "roles": ["agency_admin"],
    "is_active": True,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
  }
  await test_db.users.insert_one(doc)
  return doc


@pytest.fixture
async def feature_test_membership(test_db, feature_test_user, tenant_for_feature_test) -> str:
  """Create an active membership linking user to tenant."""
  repo = MembershipRepository(test_db)
  payload = {
    "user_id": str(feature_test_user["_id"]),
    "tenant_id": str(tenant_for_feature_test["_id"]),
    "status": "active",
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
  }
  return await repo.upsert_membership(payload)


@pytest.fixture
async def feature_test_token(feature_test_user) -> str:
  """JWT token for the feature test user."""
  org = await get_db()  # not needed, org_id is on user doc
  return create_access_token(
    subject=feature_test_user["email"],
    organization_id=feature_test_user["organization_id"],
    roles=feature_test_user["roles"],
  )


@pytest.fixture
async def feature_test_client(
  app_with_overrides,
  feature_test_token: str,
  tenant_for_feature_test,
  feature_test_membership,
) -> AsyncGenerator[AsyncClient, None]:
  """HTTP client with Bearer token + X-Tenant-Id headers for feature tests.

  This client goes through TenantResolutionMiddleware which sets
  request.state.tenant_id, enabling require_tenant_feature guards.
  """
  headers = {
    "Authorization": f"Bearer {feature_test_token}",
    "X-Tenant-Id": str(tenant_for_feature_test["_id"]),
  }
  transport = ASGITransport(app=app_with_overrides)
  async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0, headers=headers) as client:
    yield client


async def clear_features(test_db, tenant_id: str) -> None:
  """Remove all features for a tenant."""
  await test_db.tenant_features.delete_many({"tenant_id": tenant_id})


async def enable_feature(tenant_id: str, feature_key: str) -> None:
  """Enable a single feature for a tenant using the FeatureService."""
  current = await feature_service.get_features(tenant_id)
  if feature_key not in current:
    current.append(feature_key)
  await feature_service.set_features(tenant_id, current)
