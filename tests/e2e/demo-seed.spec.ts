import { test, expect } from "@playwright/test";

const BASE_URL = "https://enterprise-ops-8.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test.describe("Demo Seed", () => {
  let token: string;
  let tenantId: string;

  test.beforeAll(async ({ request }) => {
    const signup = await request.post(`${BASE_URL}/api/onboarding/signup`, {
      data: {
        company_name: `DemoSeedCo_${UID}`,
        admin_name: "Seed Admin",
        email: `seed_${UID}@test.com`,
        password: "test123456",
        plan: "starter",
        billing_cycle: "monthly",
      },
    });
    expect(signup.ok()).toBeTruthy();
    const d = await signup.json();
    token = d.access_token;
    tenantId = d.tenant_id;
  });

  test("seed demo creates expected entity counts", async ({ request }) => {
    const res = await request.post(`${BASE_URL}/api/admin/demo/seed`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { mode: "light", with_finance: true, with_crm: true },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.already_seeded).toBe(false);
    expect(body.counts.products).toBeGreaterThanOrEqual(3);
    expect(body.counts.customers).toBeGreaterThanOrEqual(5);
    expect(body.counts.reservations).toBeGreaterThanOrEqual(10);
    expect(body.counts.deals).toBeGreaterThanOrEqual(5);
    expect(body.counts.tasks).toBeGreaterThanOrEqual(10);
  });

  test("idempotent - returns already_seeded without force", async ({ request }) => {
    const res = await request.post(`${BASE_URL}/api/admin/demo/seed`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { mode: "light", with_finance: true, with_crm: true },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.already_seeded).toBe(true);
  });

  test("force re-seed works", async ({ request }) => {
    const res = await request.post(`${BASE_URL}/api/admin/demo/seed`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { mode: "light", with_finance: true, with_crm: true, force: true },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.already_seeded).toBe(false);
  });

  test("dashboard shows non-zero CRM deals after seed", async ({ request }) => {
    const deals = await request.get(`${BASE_URL}/api/crm/deals?status=open`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(deals.ok()).toBeTruthy();
    const d = await deals.json();
    expect(d.total).toBeGreaterThan(0);
  });
});
