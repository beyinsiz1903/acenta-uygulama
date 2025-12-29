const { test, expect } = require("@playwright/test");
require("dotenv").config({ path: "./.env" });

const BASE_URL = process.env.FRONTEND_URL || "http://localhost:3000";

// Helper selectors
const selectors = {
  loginEmail: "#email",
  loginPassword: "#password",
  loginSubmit: '[data-testid="login-submit"]',
};

// NOTE: This is a smoke test script intended to be run manually via Playwright,
// not wired into CI yet. Example:
//   npx playwright test frontend/tests/tour-booking.spec.js --headed

test("public tour booking -> agency sees and approves request", async ({ page }) => {
  // 1) Public: go to /tours and open first tour detail
  await page.goto(`${BASE_URL}/tours`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);

  const firstCard = page.locator("text=Turlar").locator("xpath=../../..");
  // Fallback: click first tour card link on page
  const tourLink = page.locator("a[href^='/tours/']").first();
  await tourLink.click();

  await page.waitForLoadState("networkidle");
  await expect(page.locator("text=Rezervasyon Yap")).toBeVisible();

  // 2) Open booking form and submit
  await page.click("text=Rezervasyon Yap");

  const dialog = page.locator("text=Rezervasyon Talebi");
  await expect(dialog).toBeVisible();

  // Fill form - selectors are simple because we have only one form in dialog
  const inputs = page.locator("form input");
  await inputs.nth(0).fill("Playwright Test User"); // Ad Soyad
  await inputs.nth(1).fill("+905551112233"); // Telefon
  await inputs.nth(2).fill("test@example.com"); // Email

  const dateInput = page.locator('form input[type="date"]');
  await dateInput.fill("2025-12-30");

  const paxInput = page.locator('form input[type="number"]');
  await paxInput.fill("2");

  const noteArea = page.locator("form textarea");
  await noteArea.fill("Playwright tur rezervasyon talebi");

  await page.click("button:has-text('Talep Gönder')");
  await page.waitForTimeout(1500);

  // 3) Agency login in same browser context
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.fill(selectors.loginEmail, "agency1@demo.test");
  await page.fill(selectors.loginPassword, "agency123");
  await page.click(selectors.loginSubmit);
  await page.waitForTimeout(2000);

  // 4) Go to Tur Talepleri page
  await page.goto(`${BASE_URL}/app/agency/tour-bookings`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  const list = page.locator("text=Tur Rezervasyon Talepleri");
  await expect(list).toBeVisible();

  // There should be at least one card; we check for the guest name used above
  const firstRequest = page.locator("text=Playwright Test User").first();
  await expect(firstRequest).toBeVisible();

  // 5) Approve the request and verify it moves to Approved filter
  const card = firstRequest.locator("xpath=../../..");
  await card.locator("text=Onayla").click();

  // Confirm dialog (native confirm) cannot be asserted easily here; assume OK
  await page.waitForTimeout(1500);

  // Switch filter to "Onaylandı"
  await page.click("button:has-text('Onaylandı')");
  await page.waitForTimeout(1500);

  const approvedRequest = page.locator("text=Playwright Test User").first();
  await expect(approvedRequest).toBeVisible();
});
