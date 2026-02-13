import { test, expect } from "@playwright/test";

const BASE = "https://ui-bug-fixes-13.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

async function signup(request: any) {
  const r = await request.post(`${BASE}/api/onboarding/signup`, {
    data: {
      company_name: `DSeed_${UID}`,
      admin_name: "Admin",
      email: `dseed_${UID}@test.com`,
      password: "test123456",
      plan: "starter",
      billing_cycle: "monthly",
    },
  });
  if (!r.ok()) return null;
  return (await r.json()) as { access_token: string; tenant_id: string };
}

test("demo-seed: create + idempotent + force + verify data", async ({ request }) => {
  const auth = await signup(request);
  expect(auth).toBeTruthy();
  const h = { Authorization: `Bearer ${auth!.access_token}` };

  // 1) Seed
  const s1 = await request.post(`${BASE}/api/admin/demo/seed`, {
    headers: h,
    data: { mode: "light", with_finance: true, with_crm: true },
  });
  expect(s1.ok()).toBeTruthy();
  const b1 = await s1.json();
  expect(b1.ok).toBe(true);
  expect(b1.already_seeded).toBe(false);
  expect(b1.counts.products).toBeGreaterThanOrEqual(3);
  expect(b1.counts.customers).toBeGreaterThanOrEqual(5);
  expect(b1.counts.reservations).toBeGreaterThanOrEqual(10);
  expect(b1.counts.deals).toBeGreaterThanOrEqual(5);
  expect(b1.counts.tasks).toBeGreaterThanOrEqual(10);

  // 2) Idempotent
  const s2 = await request.post(`${BASE}/api/admin/demo/seed`, {
    headers: h,
    data: { mode: "light", with_finance: true, with_crm: true },
  });
  expect(s2.ok()).toBeTruthy();
  expect((await s2.json()).already_seeded).toBe(true);

  // 3) Force
  const s3 = await request.post(`${BASE}/api/admin/demo/seed`, {
    headers: h,
    data: { mode: "light", with_finance: true, with_crm: true, force: true },
  });
  expect(s3.ok()).toBeTruthy();
  const b3 = await s3.json();
  expect(b3.ok).toBe(true);
  expect(b3.already_seeded).toBe(false);

  // 4) Verify CRM deals exist
  const deals = await request.get(`${BASE}/api/crm/deals?status=open`, { headers: h });
  expect(deals.ok()).toBeTruthy();
  expect((await deals.json()).total).toBeGreaterThan(0);
});
