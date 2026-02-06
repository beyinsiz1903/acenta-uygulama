import { test, expect } from "@playwright/test";

const BASE_URL = "https://enterprise-ops-8.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test.describe("Upgrade Request", () => {
  let tokenAdmin: string;
  let tenantId: string;

  test.beforeAll(async ({ request }) => {
    const signup = await request.post(`${BASE_URL}/api/onboarding/signup`, {
      data: {
        company_name: `UpgradeCo_${UID}`,
        admin_name: "Upgrade Admin",
        email: `upgrade_${UID}@test.com`,
        password: "test123456",
        plan: "starter",
        billing_cycle: "monthly",
      },
    });
    expect(signup.ok()).toBeTruthy();
    const d = await signup.json();
    tokenAdmin = d.access_token;
    tenantId = d.tenant_id;
  });

  test("tenant_admin creates upgrade request", async ({ request }) => {
    const res = await request.post(`${BASE_URL}/api/upgrade-requests`, {
      headers: { Authorization: `Bearer ${tokenAdmin}` },
      data: { requested_plan: "growth", message: "Need more features" },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe("pending");
    expect(body.requested_plan).toBe("growth");
  });

  test("duplicate upgrade request blocked with 409", async ({ request }) => {
    const res = await request.post(`${BASE_URL}/api/upgrade-requests`, {
      headers: { Authorization: `Bearer ${tokenAdmin}` },
      data: { requested_plan: "enterprise" },
    });
    expect(res.status()).toBe(409);
  });

  test("list upgrade requests shows pending", async ({ request }) => {
    const res = await request.get(`${BASE_URL}/api/upgrade-requests`, {
      headers: { Authorization: `Bearer ${tokenAdmin}` },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.items.length).toBeGreaterThan(0);
    expect(body.items[0].status).toBe("pending");
  });

  test("tenant_admin cannot directly change plan", async ({ request }) => {
    const res = await request.post(`${BASE_URL}/api/admin/tenants/${tenantId}/change-plan`, {
      headers: { Authorization: `Bearer ${tokenAdmin}` },
      data: { plan: "enterprise" },
    });
    // super_admin only - should get 403
    expect(res.status()).toBe(403);
  });
});
