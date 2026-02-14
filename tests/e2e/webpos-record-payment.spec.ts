// tests/e2e/webpos-record-payment.spec.ts
import { test, expect } from "@playwright/test";

const BASE_URL = "https://ui-consistency-50.preview.emergentagent.com";

async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[data-testid="login-email"]', 'admin@acenta.test');
  await page.fill('[data-testid="login-password"]', 'admin123');
  await page.click('[data-testid="login-submit"]');
  await page.waitForURL(/\/app/, { timeout: 15000 });
}

test.describe("WebPOS Record Payment", () => {
  test("webpos page loads with balance and action buttons", async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/app/finance/webpos`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator('[data-testid="webpos-page"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="balance"]')).toBeVisible();
    await expect(page.locator('[data-testid="new-payment-btn"]')).toBeVisible();
  });

  test("can open payment modal and record payment", async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/app/finance/webpos`);
    await page.waitForLoadState("networkidle");

    // Open payment modal
    await page.click('[data-testid="new-payment-btn"]');
    await expect(page.locator('[data-testid="payment-modal"]')).toBeVisible({ timeout: 5000 });

    // Fill form
    await page.fill('[data-testid="payment-amount"]', '2500');
    await page.selectOption('[data-testid="payment-method"]', 'cash');

    // Submit
    await page.click('[data-testid="payment-submit"]');

    // Modal should close
    await expect(page.locator('[data-testid="payment-modal"]')).not.toBeVisible({ timeout: 10000 });

    // Balance should be updated (visible on page)
    await page.waitForLoadState("networkidle");
    await expect(page.locator('[data-testid="balance"]')).toBeVisible();
  });

  test("ledger tab shows entries", async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/app/finance/webpos`);
    await page.waitForLoadState("networkidle");

    // Click ledger tab
    await page.click('text=Defter');
    await page.waitForTimeout(2000);

    // Should see ledger table headers (Zaman, Tür, Kategori, Tutar, Bakiye)
    const hasTable = await page.locator('table').count();
    expect(hasTable).toBeGreaterThan(0);
  });
});
