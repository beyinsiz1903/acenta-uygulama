// tests/e2e/dashboard-drilldown.spec.ts
import { test, expect } from "@playwright/test";

const BASE_URL = "https://booking-suite-pro.preview.emergentagent.com";

async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[data-testid="login-email"]', 'admin@acenta.test');
  await page.fill('[data-testid="login-password"]', 'admin123');
  await page.click('[data-testid="login-submit"]');
  await page.waitForURL(/\/app/, { timeout: 15000 });
}

test('clicking Beklemede KPI navigates to reservations with status', async ({ page }) => {
  await login(page);
  await page.goto(`${BASE_URL}/app`);
  await page.waitForLoadState('networkidle');

  const kpiBar = page.locator('[data-testid="dashboard-kpi-bar"]');
  await expect(kpiBar).toBeVisible({ timeout: 10000 });

  // Click "Beklemede" KPI card (2nd card)
  const beklemede = kpiBar.locator('> div').nth(1);
  await beklemede.click();
  await page.waitForTimeout(2000);

  // Should navigate to reservations page with status param
  expect(page.url()).toContain('reservations');
  expect(page.url()).toContain('status=pending');
});

test('notification drawer opens and closes', async ({ page }) => {
  await login(page);
  await page.goto(`${BASE_URL}/app`);
  await page.waitForLoadState('networkidle');

  // Bell button should exist
  const bell = page.locator('[data-testid="notif-bell"]');
  await expect(bell).toBeVisible({ timeout: 10000 });

  // Click bell to open drawer
  await bell.click();
  await page.waitForTimeout(1000);

  // Drawer should be visible
  const drawer = page.locator('[data-testid="notif-drawer"]');
  await expect(drawer).toBeVisible();

  // Should have tabs
  await expect(drawer.getByText('Aktiviteler')).toBeVisible();
  await expect(drawer.getByText('Uyar\u0131lar')).toBeVisible();

  // Close drawer by clicking backdrop
  await page.locator('.fixed.inset-0.bg-black\\/20').click();
  await page.waitForTimeout(500);

  // Drawer should be hidden
  await expect(drawer).not.toBeVisible();
});

test('sidebar collapse toggle works', async ({ page }) => {
  await login(page);
  await page.goto(`${BASE_URL}/app`);
  await page.waitForLoadState('networkidle');

  const sidebar = page.locator('[data-testid="sidebar"]');
  const toggle = page.locator('[data-testid="sidebar-toggle"]');

  await expect(sidebar).toBeVisible({ timeout: 10000 });
  await expect(toggle).toBeVisible();

  // Check initial width (expanded ~220px)
  const initialWidth = await sidebar.evaluate(el => el.offsetWidth);
  expect(initialWidth).toBeGreaterThan(150);

  // Click collapse
  await toggle.click();
  await page.waitForTimeout(500);

  // Width should be smaller (collapsed ~56px)
  const collapsedWidth = await sidebar.evaluate(el => el.offsetWidth);
  expect(collapsedWidth).toBeLessThan(80);

  // Section labels should be hidden
  await expect(sidebar.getByText('CORE')).not.toBeVisible();

  // Expand again
  await toggle.click();
  await page.waitForTimeout(500);

  const expandedWidth = await sidebar.evaluate(el => el.offsetWidth);
  expect(expandedWidth).toBeGreaterThan(150);

  // Labels visible again
  await expect(sidebar.getByText('CORE')).toBeVisible();
});
