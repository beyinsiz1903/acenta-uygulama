import { test, expect } from "@playwright/test";

async function loginAsAgencyAdmin(page) {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.fill('[data-testid="login-email"]', "agency1@demo.test");
  await page.fill('[data-testid="login-password"]', "agency123");
  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    page.click('[data-testid="login-submit"]'),
  ]);
  await expect(page).toHaveURL(/\/app\//, { timeout: 30000 });
}

async function ensureCatalogBooking(page) {
  // Go to products page and ensure one product + variant exists
  await page.goto("/app/agency/catalog/products", { waitUntil: "networkidle" });
  const productRows = page.locator('[data-testid="catalog-product-row"]');

  if ((await productRows.count()) === 0) {
    const titleInput = page.locator('[data-testid="catalog-product-title-input"]');
    await titleInput.fill("Offer Test Product");
    await page.click('[data-testid="btn-catalog-create-product"]');
    await expect(productRows.first()).toBeVisible({ timeout: 30000 });
  }

  await productRows.first().locator('[data-testid="btn-catalog-open-variants"]').click();
  const variantRows = page.locator('[data-testid="catalog-variant-row"]');

  if ((await variantRows.count()) === 0) {
    await page.fill('input[placeholder="Variant adı"]', "Offer Variant");
    await page.fill('input[placeholder="Fiyat"]', "1000");
    await page.fill('input[placeholder="Min pax"]', "1");
    await page.fill('input[placeholder="Max pax"]', "4");
    await page.click('[data-testid="btn-catalog-create-variant"]');
    await expect(variantRows.first()).toBeVisible({ timeout: 30000 });
  }

  // Go to bookings page
  await page.goto("/app/agency/catalog/bookings", { waitUntil: "networkidle" });

  const createBtn = page.locator('[data-testid="btn-catalog-create-booking"]');
  await expect(createBtn).toBeVisible({ timeout: 30000 });
  await createBtn.click();

  // Select product
  await page
    .locator('[data-testid="catalog-booking-select-product"]')
    .click({ timeout: 30000 });
  await page
    .locator('[data-testid="catalog-booking-product-item"]')
    .first()
    .click({ timeout: 30000 });

  // Variant is optional
  const variantItemCount = await page
    .locator('[data-testid="catalog-booking-select-variant"]')
    .count();
  if (variantItemCount > 0) {
    const variantTrigger = page.locator('[data-testid="catalog-booking-select-variant"]');
    await variantTrigger.click({ timeout: 30000 });
    // We didn't add testid to variant items, so select first option via role
    const variantOptions = page.locator("[role='option']");
    if ((await variantOptions.count()) > 0) {
      await variantOptions.first().click({ timeout: 30000 });
    }
  }

  await page
    .locator('[data-testid="catalog-booking-guest-fullname"]')
    .fill("Offer Flow Guest", { timeout: 30000 });
  await page
    .locator('[data-testid="catalog-booking-start-date"]')
    .fill("2026-01-10", { timeout: 30000 });
  await page
    .locator('[data-testid="catalog-booking-pax"]')
    .fill("2", { timeout: 30000 });

  await Promise.all([
    page.waitForURL(/\/app\/agency\/catalog\/bookings\//, { timeout: 30000 }),
    page.locator('[data-testid="btn-catalog-submit-booking"]').click(),
  ]);

  await expect(page).toHaveURL(/\/app\/agency\/catalog\/bookings\//, { timeout: 30000 });
}


test("Catalog Offer: create, send, public PDF works", async ({ page, request }) => {
  await loginAsAgencyAdmin(page);
  await ensureCatalogBooking(page);

  // We should be on booking detail page now
  await expect(page.locator('[data-testid="booking-detail-title"]')).toBeVisible({ timeout: 30000 });

  // Approve booking if possible
  const approveBtn = page.locator('[data-testid="btn-catalog-approve"]');
  if (await approveBtn.count()) {
    await approveBtn.first().click();
  }

  // Create offer draft
  const createOfferBtn = page.locator('[data-testid="btn-offer-create"]');
  await expect(createOfferBtn).toBeVisible({ timeout: 30000 });
  await createOfferBtn.click();

  // Send offer
  const sendOfferBtn = page.locator('[data-testid="btn-offer-send"]');
  await sendOfferBtn.click();

  // Wait for public URL to appear
  const urlInput = page.locator('[data-testid="offer-public-url"]');
  await expect(urlInput).toBeVisible({ timeout: 30000 });
  const relativeUrl = await urlInput.inputValue();

  // Build absolute URL using PW_BASE_URL
  const base = process.env.PW_BASE_URL || "http://localhost:3000";
  const backendBase = base.replace(/\/$/, "");
  const fullUrl = relativeUrl.startsWith("http") ? relativeUrl : backendBase.replace(/:3000$/, "") + relativeUrl;

  const response = await request.get(fullUrl);
  expect(response.status()).toBe(200);
  const contentType = response.headers()["content-type"] || "";
  expect(contentType).toContain("application/pdf");
});
