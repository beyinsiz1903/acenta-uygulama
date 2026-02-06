import { test, expect } from "@playwright/test";

const BASE = "https://enterprise-ops-8.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test("upgrade-request: create, duplicate block, list", async ({ request }) => {
  // Signup
  const su = await request.post(`${BASE}/api/onboarding/signup`, {
    data: {
      company_name: `UP_${UID}`,
      admin_name: "Admin",
      email: `up_${UID}@test.com`,
      password: "test123456",
      plan: "starter",
      billing_cycle: "monthly",
    },
  });
  expect(su.ok()).toBeTruthy();
  const { access_token: token, tenant_id: tenantId } = await su.json();
  const h = { Authorization: `Bearer ${token}` };

  // 1) Create upgrade request
  const r1 = await request.post(`${BASE}/api/upgrade-requests`, {
    headers: h,
    data: { requested_plan: "growth", message: "Need more" },
  });
  expect(r1.ok()).toBeTruthy();
  const b1 = await r1.json();
  expect(b1.status).toBe("pending");
  expect(b1.requested_plan).toBe("growth");

  // 2) Duplicate blocked
  const r2 = await request.post(`${BASE}/api/upgrade-requests`, {
    headers: h,
    data: { requested_plan: "enterprise" },
  });
  expect(r2.status()).toBe(409);

  // 3) List shows pending
  const r3 = await request.get(`${BASE}/api/upgrade-requests`, { headers: h });
  expect(r3.ok()).toBeTruthy();
  const b3 = await r3.json();
  expect(b3.items.length).toBeGreaterThan(0);
  expect(b3.items[0].status).toBe("pending");
});
