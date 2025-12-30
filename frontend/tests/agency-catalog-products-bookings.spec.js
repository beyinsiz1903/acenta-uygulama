import { test, expect } from "@playwright/test";

async function loginAsAgencyAdmin(page) {
  await page.goto("/login", { waitUntil: "domcontentloaded" });

  await page.fill('[data-testid="login-email"]', "agency1@demo.test");
  await page.fill('[data-testid="login-password"]', "agency123");

  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    page.click('[data-testid="login-submit"]'),
  ]);

  await expect(page).toHaveURL(/\/app\//, { timeout: 30_000 });
}

// Konsol hatalarını logla (runtime crash tespiti için)
function attachConsoleLogging(page) {
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      // Test logunda görelim
      console.log("BROWSER_CONSOLE_ERROR:", msg.text());
    }
  });
}

// Ana E2E akış
test("Catalog Products  Variants  Booking full flow", async ({ page }) => {
  attachConsoleLogging(page);

  // LOGIN
  await loginAsAgencyAdmin(page);

  // 1) PRODUCTS PAGE
  await page.goto("/app/agency/catalog/products", { waitUntil: "networkidle" });
  await expect(page).toHaveURL(/\/app\/agency\/catalog\/products/, { timeout: 30_000 });

  const productRows = page.locator('[data-testid="catalog-product-row"]');

  // Eğer hiç ürün yoksa bir ürün oluştur
  if ((await productRows.count()) === 0) {
    const createTitle = page.locator('[data-testid="catalog-product-title-input"]');
    await createTitle.fill("Test Katalog Turu");
    await page.click('[data-testid="btn-catalog-create-product"]');
    await expect(productRows.first()).toBeVisible({ timeout: 30_000 });
  }

  // İlk ürün için variant panelini aç
  await page.locator('[data-testid="btn-catalog-open-variants"]').first().click();

  const variantRows = page.locator('[data-testid="catalog-variant-row"]');

  // Variant yoksa bir tane oluştur
  if ((await variantRows.count()) === 0) {
    await page.fill('input[placeholder="Variant adı"]', "Standart");
    await page.fill('input[placeholder="Fiyat"]', "1000");
    await page.fill('input[placeholder="Min pax"]', "1");
    await page.fill('input[placeholder="Max pax"]', "5");
    await page.click('[data-testid="btn-catalog-create-variant"]');
    await expect(variantRows.first()).toBeVisible({ timeout: 30_000 });
  }

  // 2) BOOKINGS PAGE
  await page.goto("/app/agency/catalog/bookings", { waitUntil: "networkidle" });
  await expect(page).toHaveURL(/\/app\/agency\/catalog\/bookings/, { timeout: 30_000 });

  const createBtn = page.locator('[data-testid="btn-catalog-create-booking"]');
  await expect(createBtn).toBeVisible({ timeout: 30_000 });

  await createBtn.click();

  // Modal içinde temel alanlar (artık data-testid kullanıyoruz)
  const modal = page.locator('[data-testid="catalog-booking-create-modal"]');
  await expect(modal).toBeVisible({ timeout: 30_000 });

  // Ürün & variant select
  await page
    .locator('[data-testid="catalog-booking-select-product"]')
    .click({ timeout: 30_000 });
  await page
    .locator('[data-testid="catalog-booking-product-item"]')
    .first()
    .click({ timeout: 30_000 });

  const hasVariantItem = await page
    .locator('[data-testid="catalog-booking-variant-item"]')
    .count();
  if (hasVariantItem > 0) {
    await page
      .locator('[data-testid="catalog-booking-select-variant"]')
      .click({ timeout: 30_000 });
    await page
      .locator('[data-testid="catalog-booking-variant-item"]')
      .first()
      .click({ timeout: 30_000 });
  }

  // Guest & booking fields (tamamen data-testid üzerinden)
  await page
    .locator('[data-testid="catalog-booking-guest-fullname"]')
    .fill("Playwright Guest", { timeout: 30_000 });
  await page
    .locator('[data-testid="catalog-booking-guest-phone"]')
    .fill("05550000000", { timeout: 30_000 });
  await page
    .locator('[data-testid="catalog-booking-guest-email"]')
    .fill("pwguest@example.com", { timeout: 30_000 });
  await page
    .locator('[data-testid="catalog-booking-start-date"]')
    .fill("2026-01-10", { timeout: 30_000 });
  await page
    .locator('[data-testid="catalog-booking-pax"]')
    .fill("2", { timeout: 30_000 });
  await page
    .locator('[data-testid="catalog-booking-commission"]')
    .fill("0.10", { timeout: 30_000 });

  // Kaydet
  await Promise.all([
    page.waitForURL(/\/app\/agency\/catalog\/bookings\//, { timeout: 30_000 }),
    page.locator('[data-testid="btn-catalog-submit-booking"]').click(),
  ]);

  // DETAIL PAGE
  await expect(page).toHaveURL(/\/app\/agency\/catalog\/bookings\//, { timeout: 30_000 });

  // Internal note ekle
  await page.fill('[data-testid="internal-note-input"]', "Playwright test notu");
  await page.click('[data-testid="btn-add-internal-note"]');
  await expect(page.locator("text=Playwright test notu")).toBeVisible({ timeout: 30_000 });

  // Approve butonu görünüyorsa onayla
  const approveBtn = page.locator('[data-testid="btn-catalog-approve"]');
  if (await approveBtn.count()) {
    await approveBtn.first().click();
    await expect(page.locator("text=approved")).toBeVisible({ timeout: 30_000 });
  }
});
