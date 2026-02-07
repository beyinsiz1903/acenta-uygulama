import { test, expect } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
const BACKEND_URL = process.env.E2E_BACKEND_URL || "http://localhost:8001";
const ADMIN_EMAIL = "admin@acenta.test";
const ADMIN_PASSWORD = "admin123";

let authToken = "";

async function loginAsSuperAdmin(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState("networkidle");
  await page.getByTestId("login-email").fill(ADMIN_EMAIL);
  await page.getByTestId("login-password").fill(ADMIN_PASSWORD);
  await Promise.all([
    page.waitForURL(/\/app/, { timeout: 15000 }),
    page.getByTestId("login-submit").click(),
  ]);
}

async function getAuthToken(request) {
  const resp = await request.post(`${BACKEND_URL}/api/auth/login`, {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  });
  const body = await resp.json();
  return body.access_token;
}

test.describe("Maintenance Mode", () => {
  test("admin can toggle maintenance mode on and off", async ({ page, request }) => {
    authToken = await getAuthToken(request);

    // 1. Enable maintenance mode via API
    const enableResp = await request.patch(`${BACKEND_URL}/api/admin/tenant/maintenance`, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { maintenance_mode: true },
    });
    expect(enableResp.ok()).toBeTruthy();
    const enableBody = await enableResp.json();
    expect(enableBody.maintenance_mode).toBe(true);
    console.log("✅ Maintenance mode ENABLED via API");

    // 2. Verify maintenance status via GET
    const statusResp = await request.get(`${BACKEND_URL}/api/admin/tenant/maintenance`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(statusResp.ok()).toBeTruthy();
    const statusBody = await statusResp.json();
    expect(statusBody.maintenance_mode).toBe(true);
    console.log("✅ Maintenance mode status confirmed TRUE");

    // 3. Admin can still access the app (admin bypass)
    await loginAsSuperAdmin(page);
    await page.goto(`${BASE_URL}/app/admin/system-metrics`);
    await page.waitForLoadState("networkidle");
    const pageEl = page.getByTestId("system-metrics-page");
    await expect(pageEl).toBeVisible({ timeout: 10000 });
    console.log("✅ Admin bypass works - admin can still access pages");

    // 4. Disable maintenance mode
    const disableResp = await request.patch(`${BACKEND_URL}/api/admin/tenant/maintenance`, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { maintenance_mode: false },
    });
    expect(disableResp.ok()).toBeTruthy();
    const disableBody = await disableResp.json();
    expect(disableBody.maintenance_mode).toBe(false);
    console.log("✅ Maintenance mode DISABLED via API");

    // 5. Verify disabled status
    const finalResp = await request.get(`${BACKEND_URL}/api/admin/tenant/maintenance`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const finalBody = await finalResp.json();
    expect(finalBody.maintenance_mode).toBe(false);
    console.log("✅ Maintenance mode status confirmed FALSE");
  });
});
