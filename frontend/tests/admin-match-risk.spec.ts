import { test, expect } from "@playwright/test";

// Minimal smoke: assumes SUPER_ADMIN user exists and can log in via /login
// FRONTEND_BASE, SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD are provided via env.

const baseUrl = process.env.FRONTEND_BASE || "http://localhost:3000";
const adminEmail = process.env.SUPER_ADMIN_EMAIL || "admin@acenta.test";
const adminPassword = process.env.SUPER_ADMIN_PASSWORD || "admin123";

async function loginAsSuperAdmin(page: any) {
  await page.goto(`${baseUrl}/login`);

  // Adjust selectors to your login form; fall back to generic label-based selectors.
  const emailInput = await page
    .locator('[data-testid="login-email"]')
    .or(page.getByLabel(/email/i));
  const passwordInput = await page
    .locator('[data-testid="login-password"]')
    .or(page.getByLabel(/password/i));

  await emailInput.fill(adminEmail);
  await passwordInput.fill(adminPassword);

  const submitBtn = await page
    .locator('[data-testid="login-submit"]')
    .or(page.getByRole("button", { name: /login|giriş/i }));
  await submitBtn.click();
}

test("Admin Match Risk dashboard smoke", async ({ page }) => {
  // Login
  await loginAsSuperAdmin(page);

  // Navigate to dashboard
  await page.goto(`${baseUrl}/app/admin/reports/match-risk`);

  // Core widgets
  await expect(page.getByTestId("admin-match-risk-page")).toBeVisible();
  await expect(page.getByTestId("match-risk-from")).toBeVisible();
  await expect(page.getByTestId("match-risk-to")).toBeVisible();
  await expect(page.getByTestId("match-risk-group-by")).toBeVisible();
  await expect(page.getByTestId("match-risk-only-high-toggle")).toBeVisible();
  await expect(page.getByTestId("match-risk-export-csv")).toBeVisible();
  await expect(page.getByTestId("match-risk-period-label")).toBeVisible();

  // There should be at least a table container even if empty
  await expect(page.getByTestId("match-risk-summary-table")).toBeVisible();

  // Try to open drilldown from first available row/button if any
  const drillBtn = page.getByTestId("match-risk-drill-btn").first();
  if (await drillBtn.isVisible()) {
    await drillBtn.click();

    await expect(page.getByTestId("match-risk-drill-overlay")).toBeVisible();
    await expect(page.getByTestId("match-risk-drill-outcome-filter")).toBeVisible();

    const hasDrillTable = await page.getByTestId("match-risk-drill-table").isVisible().catch(() => false);
    if (hasDrillTable) {
      const copyBtn = page.getByTestId("match-risk-copy-ref").first();
      await expect(copyBtn).toBeVisible();
    }

    await page.getByTestId("match-risk-drill-close").click();
    await expect(page.getByTestId("match-risk-drill-overlay")).toBeHidden();
  }
});
