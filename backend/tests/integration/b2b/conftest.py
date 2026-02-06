from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
from bson import ObjectId
from httpx import AsyncClient

from app.db import get_db
from app.repositories.membership_repository import MembershipRepository
from app.security.deps_b2b import ALLOWED_B2B_ROLES


@pytest.fixture
async def org(test_db) -> dict:
  """Use default org from seed_default_org_and_users as B2B test org.

  seed_default_org_and_users already ensures an organization with slug="default"
  exists; we reuse that instead of creating a new one to stay aligned with
  existing auth/seed logic.
  """

  org = await test_db.organizations.find_one({"slug": "default"})
  assert org is not None, "default org must exist in test_db"
  return org


@pytest.fixture
async def provider_tenant(test_db, org) -> dict:
  """Create a provider tenant inside the default org.

  B2B endpoints resolve tenant by _id and enforce org match, so we link
  organization_id to the default org.
  """

  doc = {
    "_id": ObjectId(),
    "organization_id": org["_id"],
    "name": "B2B Provider Tenant",
    "slug": "b2b-provider-tenant",
    "status": "active",
    "is_active": True,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
  }
  await test_db.tenants.insert_one(doc)
  return doc


@pytest.fixture
async def seller_tenant(test_db, org) -> dict:
  doc = {
    "_id": ObjectId(),
    "organization_id": org["_id"],
    "name": "B2B Seller Tenant",
    "slug": "b2b-seller-tenant",
    "status": "active",
    "is_active": True,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
  }
  await test_db.tenants.insert_one(doc)
  return doc


@pytest.fixture
async def provider_user(test_db, org) -> dict:
  """Create a B2B-capable user for provider side.

  We reuse ALLOWED_B2B_ROLES so that deps_b2b.current_b2b_user accepts this
  account without additional changes.
  """

  email = "provider-b2b@test.local"
  roles = ["agency_admin"]
  assert any(r in ALLOWED_B2B_ROLES for r in roles), "provider_user must have B2B-allowed role"

  # Link user to default org; seed_default_org_and_users already set up org
  doc = {
    "_id": ObjectId(),
    "organization_id": org["_id"],
    "email": email,
    "name": "Provider B2B User",
    "roles": roles,
    "is_active": True,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
  }
  await test_db.users.insert_one(doc)
  return doc


@pytest.fixture
async def seller_user(test_db, org) -> dict:
  email = "seller-b2b@test.local"
  roles = ["agency_admin"]
  assert any(r in ALLOWED_B2B_ROLES for r in roles), "seller_user must have B2B-allowed role"

  doc = {
    "_id": ObjectId(),
    "organization_id": org["_id"],
    "email": email,
    "name": "Seller B2B User",
    "roles": roles,
    "is_active": True,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
  }
  await test_db.users.insert_one(doc)
  return doc


@pytest.fixture
async def provider_membership(test_db, provider_user, provider_tenant) -> str:
  repo = MembershipRepository(test_db)
  payload = {
    "user_id": str(provider_user["_id"]),
    "tenant_id": str(provider_tenant["_id"]),
    "status": "active",
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
  }
  membership_id = await repo.upsert_membership(payload)
  return membership_id


@pytest.fixture
async def seller_membership(test_db, seller_user, seller_tenant) -> str:
  repo = MembershipRepository(test_db)
  payload = {
    "user_id": str(seller_user["_id"]),
    "tenant_id": str(seller_tenant["_id"]),
    "status": "active",
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
  }
  membership_id = await repo.upsert_membership(payload)
  return membership_id


async def _make_token(email: str, org_id: str, roles: list[str]) -> str:
  from app.auth import create_access_token

  return create_access_token(subject=email, organization_id=str(org_id), roles=roles)


@pytest.fixture
async def provider_token(provider_user, org) -> str:
  return await _make_token(provider_user["email"], org["_id"], provider_user["roles"])


@pytest.fixture
async def seller_token(seller_user, org) -> str:
  return await _make_token(seller_user["email"], org["_id"], seller_user["roles"])


@pytest.fixture
async def provider_client(async_client: AsyncClient, provider_token: str, provider_tenant, provider_membership) -> AsyncGenerator[AsyncClient, None]:
  headers = {
    "Authorization": f"Bearer {provider_token}",
    "X-Tenant-Id": str(provider_tenant["_id"]),
  }
  async_client.headers.update(headers)
  yield async_client


@pytest.fixture
async def seller_client(async_client: AsyncClient, seller_token: str, seller_tenant, seller_membership) -> AsyncGenerator[AsyncClient, None]:
  headers = {
    "Authorization": f"Bearer {seller_token}",
    "X-Tenant-Id": str(seller_tenant["_id"]),
  }
  async_client.headers.update(headers)
  yield async_client


@pytest.fixture
async def partner_relationship_active(test_db, org, provider_tenant, seller_tenant) -> dict:
  """Active partner relationship between provider_tenant and seller_tenant.

  We align field names with b2b_exchange.list_available_listings which uses
  seller_tenant_id / buyer_tenant_id and status="active".
  """

  now = datetime.now(timezone.utc)
  doc = {
    "_id": ObjectId(),
    "seller_tenant_id": str(provider_tenant["_id"]),
    "buyer_tenant_id": str(seller_tenant["_id"]),
    "status": "active",
    "created_at": now,
    "updated_at": now,
    "seller_org_id": str(org["_id"]),
    "buyer_org_id": str(org["_id"]),
  }
  await test_db.partner_relationships.insert_one(doc)
  return doc
