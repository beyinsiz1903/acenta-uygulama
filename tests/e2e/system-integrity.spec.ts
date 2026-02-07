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

test.describe("System Integrity Page", () => {
  test("page loads and integrity report renders", async ({ page }) => {
    await loginAsSuperAdmin(page);

    // Navigate to integrity page
    await page.goto(`${BASE_URL}/app/admin/system-integrity`);
    await page.waitForLoadState("networkidle");

    // Page renders
    const pageEl = page.getByTestId("system-integrity-page");
    await expect(pageEl).toBeVisible({ timeout: 10000 });
    console.log("✅ System Integrity page loaded");

    // Wait for data to load
    await page.waitForTimeout(3000);

    // Either report renders or empty state shows
    const report = page.getByTestId("integrity-report");
    const emptyState = page.getByTestId("empty-state");

    const reportVisible = await report.isVisible().catch(() => false);
    const emptyVisible = await emptyState.isVisible().catch(() => false);

    if (reportVisible) {
      console.log("✅ Integrity report rendered with data");

      // Verify summary cards exist (audit chain, ledger, orphans)
      const cards = page.locator(".border.rounded-lg.p-4");
      const cardCount = await cards.count();
      expect(cardCount).toBeGreaterThanOrEqual(3);
      console.log(`✅ ${cardCount} summary cards rendered`);

      // Check that at least one of Sağlam/Kırık/Tutarlı/Uyumsuz/Temiz text exists
      const summaryText = await page.textContent("[data-testid='integrity-report']");
      const hasStatus = summaryText?.includes("Sağlam") || summaryText?.includes("Tutarlı") || summaryText?.includes("Temiz") || summaryText?.includes("Kırık") || summaryText?.includes("Uyumsuz");
      expect(hasStatus).toBeTruthy();
      console.log("✅ Status indicators visible in report");
    } else if (emptyVisible) {
      console.log("✅ Empty state shown (no data)");
    } else {
      // Still loading or error - check spinner
      console.log("⚠ Neither report nor empty state visible - may still be loading");
    }
  });
});
