// tests/e2e/tenant-isolation.spec.ts
import { test, expect } from "@playwright/test";

const BASE_URL = "https://data-sync-tool-1.preview.emergentagent.com";
const UNIQUE = Date.now().toString(36);

test.describe("Tenant Isolation", () => {
  test("two tenants cannot see each other's data", async ({ request }) => {
    // Create Tenant A
    const signupA = await request.post(`${BASE_URL}/api/onboarding/signup`, {
      data: {
        company_name: `TenantA_${UNIQUE}`,
        admin_name: "Admin A",
        email: `tenantA_${UNIQUE}@test.com`,
        password: "test123456",
        plan: "pro",
        billing_cycle: "monthly",
      },
    });
    expect(signupA.ok()).toBeTruthy();
    const dataA = await signupA.json();
    const tokenA = dataA.access_token;

    // Create Tenant B
    const signupB = await request.post(`${BASE_URL}/api/onboarding/signup`, {
      data: {
        company_name: `TenantB_${UNIQUE}`,
        admin_name: "Admin B",
        email: `tenantB_${UNIQUE}@test.com`,
        password: "test123456",
        plan: "starter",
        billing_cycle: "monthly",
      },
    });
    expect(signupB.ok()).toBeTruthy();
    const dataB = await signupB.json();
    const tokenB = dataB.access_token;

    // Tenant A records a payment
    const payA = await request.post(`${BASE_URL}/api/webpos/payments`, {
      headers: { Authorization: `Bearer ${tokenA}` },
      data: { amount: 9999, currency: "TRY", method: "cash", description: "TenantA payment" },
    });
    expect(payA.ok()).toBeTruthy();

    // Tenant B checks payments - should NOT see Tenant A's payment
    const listB = await request.get(`${BASE_URL}/api/webpos/payments`, {
      headers: { Authorization: `Bearer ${tokenB}` },
    });
    expect(listB.ok()).toBeTruthy();
    const paymentsB = await listB.json();
    const bHasAPayment = (paymentsB.items || []).some(
      (p: any) => p.description === "TenantA payment" || p.amount === 9999
    );
    expect(bHasAPayment).toBeFalsy();

    // Tenant B checks ledger - should be empty
    const ledgerB = await request.get(`${BASE_URL}/api/webpos/ledger`, {
      headers: { Authorization: `Bearer ${tokenB}` },
    });
    expect(ledgerB.ok()).toBeTruthy();
    const ledgerDataB = await ledgerB.json();
    expect(ledgerDataB.total).toBe(0);

    // Tenant A sees their payment
    const listA = await request.get(`${BASE_URL}/api/webpos/payments`, {
      headers: { Authorization: `Bearer ${tokenA}` },
    });
    expect(listA.ok()).toBeTruthy();
    const paymentsA = await listA.json();
    const aHasPayment = (paymentsA.items || []).some(
      (p: any) => p.description === "TenantA payment"
    );
    expect(aHasPayment).toBeTruthy();

    // Tenant B notifications empty, tenant A notifications empty (no triggers fired)
    const notifsB = await request.get(`${BASE_URL}/api/notifications`, {
      headers: { Authorization: `Bearer ${tokenB}` },
    });
    expect(notifsB.ok()).toBeTruthy();
  });

  test("unauthenticated requests to protected endpoints fail", async ({ request }) => {
    const resp = await request.get(`${BASE_URL}/api/webpos/payments`);
    expect(resp.status()).toBe(401);

    const resp2 = await request.get(`${BASE_URL}/api/notifications`);
    expect(resp2.status()).toBe(401);

    const resp3 = await request.get(`${BASE_URL}/api/reports/financial-summary`);
    expect(resp3.status()).toBe(401);
  });
});
