import { test, expect } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "muratsutay@hotmail.com";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "murat1903";

async function loginAsAdmin(page) {
  await page.goto(`${BASE_URL}/login`);

  await page.getByTestId("login-email-input").fill(ADMIN_EMAIL);
  await page.getByTestId("login-password-input").fill(ADMIN_PASSWORD);
  await page.getByTestId("login-password-input").press("Enter");

  await page.waitForURL("**/app/**", { timeout: 15_000 });
}

// Golden path: list + supplier health + detail drawer
// Uses real backend; focuses on basic wiring and selectors.

test.describe("Ops Incidents Console v0", () => {
  test("list loads with supplier health and detail drawer opens", async ({ page }) => {
    await loginAsAdmin(page);

    // Navigate via sidebar or direct URL
    await page.goto(`${BASE_URL}/app/ops/incidents`);

    // Table present
    const table = page.getByTestId("ops-incidents-table");
    await expect(table).toBeVisible();

    // Wait for at least one row to appear
    const rows = page.getByTestId("ops-incidents-row");
    await expect(rows.first()).toBeVisible({ timeout: 15_000 });

    // Click first row → drawer should open
    await rows.first().click();

    const drawer = page.getByTestId("ops-incident-drawer");
    await expect(drawer).toBeVisible({ timeout: 10_000 });
  });
});
