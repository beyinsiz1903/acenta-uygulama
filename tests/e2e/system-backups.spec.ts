import { test, expect } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
const BACKEND_URL = process.env.E2E_BACKEND_URL || "http://localhost:8001";
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

test.describe("System Backups Page", () => {
  test("page loads, run backup, delete backup", async ({ page }) => {
    await loginAsSuperAdmin(page);

    // Navigate to system backups page
    await page.goto(`${BASE_URL}/app/admin/system-backups`);
    await page.waitForLoadState("networkidle");

    // Page renders
    const pageEl = page.getByTestId("system-backups-page");
    await expect(pageEl).toBeVisible({ timeout: 10000 });
    console.log("✅ System Backups page loaded");

    // Click "Run Backup" button
    const runBtn = page.getByTestId("run-backup-btn");
    await expect(runBtn).toBeVisible();
    await runBtn.click();
    console.log("Clicked Run Backup");

    // Wait for the backup to complete and list to refresh
    await page.waitForTimeout(3000);

    // Verify table appears with at least 1 row
    const table = page.getByTestId("backups-table");
    await expect(table).toBeVisible({ timeout: 15000 });
    const rows = table.locator("tbody tr");
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThanOrEqual(1);
    console.log(`✅ Backup created, ${rowCount} backup(s) in list`);

    // Delete the first backup
    const deleteBtn = rows.first().locator("button").last();
    await deleteBtn.click();

    // Handle confirm dialog
    page.on("dialog", async (dialog) => {
      await dialog.accept();
    });

    await page.waitForTimeout(2000);
    console.log("✅ Delete backup clicked");
  });
});
