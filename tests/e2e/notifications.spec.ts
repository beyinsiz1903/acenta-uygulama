// tests/e2e/notifications.spec.ts
import { test, expect } from "@playwright/test";

const BASE_URL = "https://billing-dashboard-v5.preview.emergentagent.com";

async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[data-testid="login-email"]', 'admin@acenta.test');
  await page.fill('[data-testid="login-password"]', 'admin123');
  await page.click('[data-testid="login-submit"]');
  await page.waitForURL(/\/app/, { timeout: 15000 });
}

test.describe("In-App Notification Engine", () => {
  test("notification bell is visible in header", async ({ page }) => {
    await login(page);
    await page.waitForLoadState("networkidle");

    // Bell should be visible in header
    await expect(page.locator('[data-testid="notification-bell"]')).toBeVisible({ timeout: 10000 });
  });

  test("clicking bell opens notification dropdown", async ({ page }) => {
    await login(page);
    await page.waitForLoadState("networkidle");

    // Click bell
    await page.click('[data-testid="notification-bell"]');

    // Dropdown should appear
    await expect(page.locator('[data-testid="notification-dropdown"]')).toBeVisible({ timeout: 5000 });

    // Should show 'Bildirimler' heading
    await expect(page.locator('[data-testid="notification-dropdown"]').getByText('Bildirimler')).toBeVisible();
  });

  test("clicking bell again closes dropdown", async ({ page }) => {
    await login(page);
    await page.waitForLoadState("networkidle");

    // Open
    await page.click('[data-testid="notification-bell"]');
    await expect(page.locator('[data-testid="notification-dropdown"]')).toBeVisible({ timeout: 5000 });

    // Close by clicking bell again
    await page.click('[data-testid="notification-bell"]');
    await expect(page.locator('[data-testid="notification-dropdown"]')).not.toBeVisible({ timeout: 3000 });
  });
});
