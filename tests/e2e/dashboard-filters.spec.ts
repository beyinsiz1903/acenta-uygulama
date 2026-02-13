// tests/e2e/dashboard-filters.spec.ts
import { test, expect } from "@playwright/test";

const BASE_URL = "https://nostalgic-ganguly-1.preview.emergentagent.com";

async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[data-testid="login-email"]', 'admin@acenta.test');
  await page.fill('[data-testid="login-password"]', 'admin123');
  await page.click('[data-testid="login-submit"]');
  await page.waitForURL(/\/app/, { timeout: 15000 });
}

test('clicking preset 14D and Apply updates URL', async ({ page }) => {
  await login(page);
  await page.goto(`${BASE_URL}/app`);
  await page.waitForLoadState('networkidle');

  const filterBar = page.locator('[data-testid="dashboard-filter-bar"]');
  await expect(filterBar).toBeVisible({ timeout: 10000 });

  // Click 14G preset
  await filterBar.getByText('14G', { exact: true }).click();

  // Click Apply
  await page.locator('[data-testid="filter-apply"]').click();
  await page.waitForTimeout(1000);

  // URL should have preset=14d
  expect(page.url()).toContain('preset=14d');
});

test('density toggle changes between compact and comfort', async ({ page }) => {
  await login(page);
  await page.goto(`${BASE_URL}/app`);
  await page.waitForLoadState('networkidle');

  // Find density toggle
  const densityBtn = page.locator('[data-testid="density-toggle"]');
  await expect(densityBtn).toBeVisible({ timeout: 10000 });

  // Default should show "Rahat" (meaning current is compact, click to switch to comfort)
  await expect(densityBtn).toContainText('Rahat');

  // Click to switch to comfort
  await densityBtn.click();
  await page.waitForTimeout(500);

  // Now should show "Kompakt" (current is comfort, click to switch back)
  await expect(densityBtn).toContainText('Kompakt');

  // Click back to compact
  await densityBtn.click();
  await page.waitForTimeout(500);
  await expect(densityBtn).toContainText('Rahat');
});

test('CSV export button exists and is clickable', async ({ page }) => {
  await login(page);
  await page.goto(`${BASE_URL}/app`);
  await page.waitForLoadState('networkidle');

  const exportBtn = page.locator('[data-testid="filter-export"]');
  await expect(exportBtn).toBeVisible({ timeout: 10000 });
  await expect(exportBtn).toContainText('CSV');

  // Click export (file download - just ensure no error)
  await exportBtn.click();
  await page.waitForTimeout(500);
  // If no errors thrown, export is working
});
