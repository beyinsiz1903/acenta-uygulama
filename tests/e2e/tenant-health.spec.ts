import { test, expect } from "@playwright/test";

const BASE = "https://test-data-populator.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test("tenant-health: loads data with filters", async ({ request }) => {
  // Signup
  const su = await request.post(`${BASE}/api/onboarding/signup`, {
    data: {
      company_name: `TH_${UID}`,
      admin_name: "Admin",
      email: `th_${UID}@test.com`,
      password: "test123456",
      plan: "starter",
      billing_cycle: "monthly",
    },
  });
  expect(su.ok()).toBeTruthy();
  const { access_token: token } = await su.json();
  const h = { Authorization: `Bearer ${token}` };

  // 1) All tenants
  const r1 = await request.get(`${BASE}/api/admin/tenants/health`, { headers: h });
  expect(r1.ok()).toBeTruthy();
  const b1 = await r1.json();
  expect(Array.isArray(b1.items)).toBe(true);
  expect(b1.items.length).toBeGreaterThan(0);

  // 2) trial_expiring filter
  const r2 = await request.get(`${BASE}/api/admin/tenants/health?filter_type=trial_expiring`, { headers: h });
  expect(r2.ok()).toBeTruthy();
  expect(Array.isArray((await r2.json()).items)).toBe(true);

  // 3) inactive filter
  const r3 = await request.get(`${BASE}/api/admin/tenants/health?filter_type=inactive`, { headers: h });
  expect(r3.ok()).toBeTruthy();
  expect(Array.isArray((await r3.json()).items)).toBe(true);

  // 4) overdue filter
  const r4 = await request.get(`${BASE}/api/admin/tenants/health?filter_type=overdue`, { headers: h });
  expect(r4.ok()).toBeTruthy();
  expect(Array.isArray((await r4.json()).items)).toBe(true);
});
