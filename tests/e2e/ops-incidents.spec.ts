import { test, expect } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "muratsutay@hotmail.com";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "murat1903";

async function loginAsSuperAdmin(page) {
  await page.goto(`${BASE_URL}/login`);

  const emailInput = page.getByTestId("login-email");
  const passwordInput = page.getByTestId("login-password");
  const submitButton = page.getByTestId("login-submit");

  await emailInput.fill(ADMIN_EMAIL);
  await passwordInput.fill(ADMIN_PASSWORD);

  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    submitButton.click(),
  ]);
}

// Golden path: list + supplier health + detail drawer
// Uses real backend; focuses on basic wiring and selectors.

test.describe("Ops Incidents Console v0", () => {
  test("list + filters + supplier health badges + drawer", async ({ page }) => {
    await loginAsSuperAdmin(page);

    // Stub list + detail endpoints for deterministic UI
    let lastListUrl: string | null = null;

    await page.route("**/api/admin/ops/incidents**", async (route) => {
      const url = new URL(route.request().url());
      lastListUrl = url.toString();

      const includeHealth = url.searchParams.get("include_supplier_health");
      expect(includeHealth).toBe("true");

      const listFixture = require("./fixtures/ops-incidents-list.json");
      await route.fulfill({ json: listFixture });
    });

    await page.route("**/api/admin/ops/incidents/inc_aaa111**", async (route) => {
      const detailFixture = require("./fixtures/ops-incidents-detail-inc_aaa111.json");
      await route.fulfill({ json: detailFixture });
    });

    // Navigate via sidebar or direct URL
    await page.goto(`${BASE_URL}/app/ops/incidents`);

    // Table present
    const table = page.getByTestId("ops-incidents-table");
    await expect(table).toBeVisible();

    // Badge states from list fixture
    await expect(page.getByTestId("ops-incidents-health-open")).toBeVisible();
    await expect(page.getByTestId("ops-incidents-health-no-health")).toBeVisible();

    // Filters: change type and ensure list endpoint is called with updated params
    await page.getByTestId("ops-incidents-filter-type").click();
    await page.getByRole("option", { name: "risk_review" }).click();

    // Allow network/route to process
    await page.waitForTimeout(200);
    expect(lastListUrl).not.toBeNull();
    if (lastListUrl) {
      const url = new URL(lastListUrl);
      expect(url.searchParams.get("type")).toBe("risk_review");
    }

    // Row click 19 drawer open + detail endpoint called
    const rows = page.getByTestId("ops-incidents-row");
    await expect(rows.first()).toBeVisible({ timeout: 15_000 });
    await rows.first().click();

    const drawer = page.getByTestId("ops-incident-drawer");
    await expect(drawer).toBeVisible({ timeout: 10_000 });

    // Drawer supplier health panel
    const healthPanel = page.getByTestId("ops-incident-drawer-health");
    await expect(healthPanel).toBeVisible();
  });
});
