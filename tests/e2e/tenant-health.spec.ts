import { test, expect } from "@playwright/test";

const BASE_URL = "https://enterprise-ops-8.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test.describe("Tenant Health", () => {
  let token: string;

  test.beforeAll(async ({ request }) => {
    const signup = await request.post(`${BASE_URL}/api/onboarding/signup`, {
      data: {
        company_name: `HealthCo_${UID}`,
        admin_name: "Health Admin",
        email: `health_${UID}@test.com`,
        password: "test123456",
        plan: "starter",
        billing_cycle: "monthly",
      },
    });
    expect(signup.ok()).toBeTruthy();
    const d = await signup.json();
    token = d.access_token;
  });

  test("health endpoint returns items array", async ({ request }) => {
    const res = await request.get(`${BASE_URL}/api/admin/tenants/health`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.items)).toBe(true);
    expect(body.items.length).toBeGreaterThan(0);
  });

  test("trial_expiring filter works", async ({ request }) => {
    const res = await request.get(`${BASE_URL}/api/admin/tenants/health?filter_type=trial_expiring`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.items)).toBe(true);
  });

  test("inactive filter works", async ({ request }) => {
    const res = await request.get(`${BASE_URL}/api/admin/tenants/health?filter_type=inactive`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.items)).toBe(true);
  });

  test("overdue filter works", async ({ request }) => {
    const res = await request.get(`${BASE_URL}/api/admin/tenants/health?filter_type=overdue`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body.items)).toBe(true);
  });
});
