import { test, expect } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
const ADMIN_EMAIL = "admin@acenta.test";
const ADMIN_PASSWORD = "admin123";

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

test.describe("System Metrics Page", () => {
  test("metrics cards render with numeric values", async ({ page }) => {
    await loginAsSuperAdmin(page);

    // Navigate to system metrics
    await page.goto(`${BASE_URL}/app/admin/system-metrics`);
    await page.waitForLoadState("networkidle");

    // Page renders
    const pageEl = page.getByTestId("system-metrics-page");
    await expect(pageEl).toBeVisible({ timeout: 10000 });
    console.log("✅ System Metrics page loaded");

    // Wait for data
    await page.waitForTimeout(3000);

    const metricsData = page.getByTestId("metrics-data");
    await expect(metricsData).toBeVisible({ timeout: 10000 });
    console.log("✅ Metrics data rendered");

    // Check metric cards are present (8 cards expected)
    const cards = metricsData.locator(".border.rounded-lg.p-4");
    const cardCount = await cards.count();
    expect(cardCount).toBeGreaterThanOrEqual(8);
    console.log(`✅ ${cardCount} metric cards rendered`);

    // Verify numeric values exist in the text
    const pageText = await metricsData.textContent();

    // avg_request_latency_ms should show "ms" suffix
    expect(pageText).toContain("ms");
    console.log("✅ Latency metric has ms suffix");

    // error_rate_percent should show "%" suffix
    const percentCount = (pageText?.match(/%/g) || []).length;
    expect(percentCount).toBeGreaterThanOrEqual(2); // error_rate + disk_usage
    console.log(`✅ Found ${percentCount} percentage metrics`);

    // Verify some labels
    expect(pageText).toContain("Aktif Tenant");
    expect(pageText).toContain("Toplam Kullanıcı");
    expect(pageText).toContain("Hata Oranı");
    expect(pageText).toContain("Disk Kullanımı");
    console.log("✅ All expected metric labels present");
  });
});
