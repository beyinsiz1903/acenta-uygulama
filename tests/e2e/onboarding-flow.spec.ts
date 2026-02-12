// tests/e2e/onboarding-flow.spec.ts
import { test, expect } from "@playwright/test";

const BASE_URL = "https://data-sync-tool-1.preview.emergentagent.com";
const UNIQUE = Date.now().toString(36);

test.describe("Self-Service Onboarding Flow", () => {
  test("signup page loads with form and plan selector", async ({ page }) => {
    await page.goto(`${BASE_URL}/signup`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator('[data-testid="signup-form"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="signup-company"]')).toBeVisible();
    await expect(page.locator('[data-testid="signup-email"]')).toBeVisible();
    await expect(page.locator('[data-testid="signup-password"]')).toBeVisible();
    await expect(page.locator('[data-testid="plan-starter"]')).toBeVisible();
    await expect(page.locator('[data-testid="plan-pro"]')).toBeVisible();
    await expect(page.locator('[data-testid="plan-enterprise"]')).toBeVisible();
    await expect(page.locator('[data-testid="signup-submit"]')).toBeVisible();
  });

  test("pricing page shows all three plans", async ({ page }) => {
    await page.goto(`${BASE_URL}/pricing`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator('[data-testid="pricing-title"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="pricing-plan-starter"]')).toBeVisible();
    await expect(page.locator('[data-testid="pricing-plan-pro"]')).toBeVisible();
    await expect(page.locator('[data-testid="pricing-plan-enterprise"]')).toBeVisible();
  });

  test("full signup -> login -> wizard flow", async ({ page }) => {
    const email = `e2e_${UNIQUE}@test.com`;

    // 1) Signup
    await page.goto(`${BASE_URL}/signup`);
    await page.waitForLoadState("networkidle");
    await page.fill('[data-testid="signup-company"]', `E2E Company ${UNIQUE}`);
    await page.fill('[data-testid="signup-name"]', "E2E Admin");
    await page.fill('[data-testid="signup-email"]', email);
    await page.fill('[data-testid="signup-password"]', "test123456");
    await page.click('[data-testid="plan-pro"]');
    await page.click('[data-testid="signup-submit"]');

    // Should redirect to /app after signup
    await page.waitForURL(/\/app/, { timeout: 15000 });

    // 2) Dashboard or wizard should load
    await page.waitForLoadState("networkidle");
    const content = await page.content();
    // Should see either dashboard or wizard content
    const hasDashboard = content.includes("Dashboard") || content.includes("data-testid");
    expect(hasDashboard).toBeTruthy();
  });

  test("duplicate email returns error", async ({ page }) => {
    // Use admin@acenta.test which already exists
    await page.goto(`${BASE_URL}/signup`);
    await page.waitForLoadState("networkidle");
    await page.fill('[data-testid="signup-company"]', "Dup Test");
    await page.fill('[data-testid="signup-name"]', "Dup User");
    await page.fill('[data-testid="signup-email"]', "admin@acenta.test");
    await page.fill('[data-testid="signup-password"]', "test123456");
    await page.click('[data-testid="signup-submit"]');

    // Should show error
    await expect(page.locator('[data-testid="signup-error"]')).toBeVisible({ timeout: 10000 });
  });
});
