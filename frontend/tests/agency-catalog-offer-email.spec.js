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

async function ensureCatalogOfferBooking(page) {
  // Reuse FAZ-3 style flow: create product+variant+booking+approve
  await page.goto("/app/agency/catalog/products", { waitUntil: "networkidle" });
  const productRows = page.locator('[data-testid="catalog-product-row"]');

  if ((await productRows.count()) === 0) {
    const titleInput = page.locator('[data-testid="catalog-product-title-input"]');
    await titleInput.fill("Offer Email Product");
    await page.click('[data-testid="btn-catalog-create-product"]');
    await expect(productRows.first()).toBeVisible({ timeout: 30000 });
  }

  await productRows.first().locator('[data-testid="btn-catalog-open-variants"]').click();
  const variantRows = page.locator('[data-testid="catalog-variant-row"]');

  if ((await variantRows.count()) === 0) {
    await page.fill('input[placeholder="Variant adı"]', "Email Variant");
    await page.fill('input[placeholder="Fiyat"]', "1000");
    await page.fill('input[placeholder="Min pax"]', "1");
    await page.fill('input[placeholder="Max pax"]', "5");
    await page.click('[data-testid="btn-catalog-create-variant"]');
    await expect(variantRows.first()).toBeVisible({ timeout: 30000 });
  }

  // Create booking via UI with guest email
  await page.goto("/app/agency/catalog/bookings", { waitUntil: "networkidle" });
  const createBtn = page.locator('[data-testid="btn-catalog-create-booking"]');
  await expect(createBtn).toBeVisible({ timeout: 30000 });
  await createBtn.click();

  await expect(page.locator('[data-testid="catalog-booking-create-modal"]')).toBeVisible({ timeout: 30000 });

  await page.locator('[data-testid="catalog-booking-select-product"]').click();
  await page.locator('[data-testid="catalog-booking-product-item"]').first().click();

  const hasVariantTrigger = await page.locator('[data-testid="catalog-booking-select-variant"]').count();
  if (hasVariantTrigger > 0) {
    const trigger = page.locator('[data-testid="catalog-booking-select-variant"]');
    await trigger.click();
    const options = page.locator("[role='option']");
    if (await options.count()) {
      await options.first().click();
    }
  }

  await page.locator('[data-testid="catalog-booking-guest-fullname"]').fill("Offer Email Guest");
  await page.locator('[data-testid="catalog-booking-guest-email"]').fill("pwguest@example.com");
  await page.locator('[data-testid="catalog-booking-start-date"]').fill("2030-03-10");
  await page.locator('[data-testid="catalog-booking-pax"]').fill("2");

  await Promise.all([
    page.waitForURL(/\/app\/agency\/catalog\/bookings\//, { timeout: 30000 }),
    page.locator('[data-testid="btn-catalog-submit-booking"]').click(),
  ]);

  await expect(page).toHaveURL(/\/app\/agency\/catalog\/bookings\//, { timeout: 30000 });

  // Approve booking if approve button exists
  const approveBtn = page.locator('[data-testid="btn-catalog-approve"]');
  if (await approveBtn.count()) {
    await approveBtn.first().click();
  }
}


test("Catalog Offer Email: send via Resend and expose metadata", async ({ page }) => {
  await loginAsAgencyAdmin(page);
  await ensureCatalogOfferBooking(page);

  // We are on booking detail page after creation + approve
  await expect(page.locator('[data-testid="booking-detail-title"]')).toBeVisible({ timeout: 30000 });

  const sendEmailBtn = page.locator('[data-testid="btn-offer-send-email"]');
  await expect(sendEmailBtn).toBeVisible({ timeout: 30000 });

  await sendEmailBtn.click();

  // Expect toast visually is hard; instead wait for email metadata to appear
  const emailTo = page.locator('[data-testid="offer-email-to"]');
  const providerId = page.locator('[data-testid="offer-email-provider-id"]');

  await expect(emailTo).toContainText("pwguest@example.com", { timeout: 30000 });
  await expect(providerId).not.toHaveText("Provider ID: ", { timeout: 30000 });
});
