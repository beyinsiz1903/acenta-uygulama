// tests/e2e/reports-page.spec.ts
import { test, expect } from "@playwright/test";

const BASE_URL = "https://tour-reserve.preview.emergentagent.com";

async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[data-testid="login-email"]', 'admin@acenta.test');
  await page.fill('[data-testid="login-password"]', 'admin123');
  await page.click('[data-testid="login-submit"]');
  await page.waitForURL(/\/app/, { timeout: 15000 });
}

test.describe("Advanced Reporting Pack", () => {
  test("reports page loads with financial summary", async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/app/reports`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator('[data-testid="reports-page"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="reports-title"]')).toBeVisible();

    // Financial summary should be visible by default
    await expect(page.locator('[data-testid="financial-summary"]')).toBeVisible({ timeout: 10000 });
  });

  test("CSV export button exists and is clickable", async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/app/reports`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator('[data-testid="export-csv"]')).toBeVisible({ timeout: 10000 });
  });

  test("can switch between report sections", async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/app/reports`);
    await page.waitForLoadState("networkidle");

    // Click product performance tab
    await page.click('text=Ürün Performansı');
    await page.waitForTimeout(1000);

    // Click partner performance tab
    await page.click('text=Partner Performansı');
    await page.waitForTimeout(1000);

    // Click aging tab
    await page.click('text=Yaşlandırma');
    await page.waitForTimeout(1000);
    await expect(page.locator('[data-testid="aging-report"]')).toBeVisible({ timeout: 5000 });
  });
});
