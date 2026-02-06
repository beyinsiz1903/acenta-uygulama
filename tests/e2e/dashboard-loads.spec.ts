// tests/e2e/dashboard-loads.spec.ts
import { test, expect } from "@playwright/test";

const BASE_URL = "https://dashboard-refresh-32.preview.emergentagent.com";

async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[data-testid="login-email"]', 'admin@acenta.test');
  await page.fill('[data-testid="login-password"]', 'admin123');
  await page.click('[data-testid="login-submit"]');
  await page.waitForURL(/\/app/, { timeout: 15000 });
}

test('dashboard loads with KPI bar visible', async ({ page }) => {
  await login(page);
  await page.goto(`${BASE_URL}/app`);
  await page.waitForLoadState('networkidle');

  // KPI bar should be visible
  const kpiBar = page.locator('[data-testid="dashboard-kpi-bar"]');
  await expect(kpiBar).toBeVisible({ timeout: 10000 });

  // Should have 6 KPI cards
  const kpiCards = kpiBar.locator('> div');
  await expect(kpiCards).toHaveCount(6);

  // Check labels
  await expect(page.getByText('Toplam Rezervasyon')).toBeVisible();
  await expect(page.getByText('Beklemede')).toBeVisible();
  await expect(page.getByText('Açık Case')).toBeVisible();
});

test('dashboard loads with filter bar visible', async ({ page }) => {
  await login(page);
  await page.goto(`${BASE_URL}/app`);
  await page.waitForLoadState('networkidle');

  // Filter bar should be visible
  const filterBar = page.locator('[data-testid="dashboard-filter-bar"]');
  await expect(filterBar).toBeVisible({ timeout: 10000 });

  // Preset buttons should exist
  await expect(filterBar.getByText('30G')).toBeVisible();
  await expect(filterBar.getByText('14G')).toBeVisible();
  await expect(filterBar.getByText('7G')).toBeVisible();

  // Apply button should exist
  const applyBtn = page.locator('[data-testid="filter-apply"]');
  await expect(applyBtn).toBeVisible();
});

test('sidebar is visible and has grouped sections', async ({ page }) => {
  await login(page);
  await page.goto(`${BASE_URL}/app`);
  await page.waitForLoadState('networkidle');

  // Sidebar should be present
  const sidebar = page.locator('[data-testid="sidebar"]');
  await expect(sidebar).toBeVisible({ timeout: 10000 });

  // Should have section headers
  await expect(sidebar.getByText('CORE')).toBeVisible();
  await expect(sidebar.getByText('CRM')).toBeVisible();

  // Dashboard link should be active
  const dashLink = sidebar.locator('a[href="/app"]');
  await expect(dashLink).toBeVisible();
});
