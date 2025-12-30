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

  // Modal içinde temel alanlar (mevcut DOM'a göre)
  const modal = page.locator(".fixed >> text=Yeni Katalog Rezervasyonu");
  await expect(modal).toBeVisible({ timeout: 30_000 });

  // Ürün select: fixed container içindeki ilk select
  const selects = page.locator(".fixed select");
  await expect(selects.first()).toBeVisible({ timeout: 30_000 });

  const selectCount = await selects.count();
  if (selectCount >= 1) {
    await selects.nth(0).selectOption({ index: 0 });
  }
  if (selectCount >= 2) {
    const hasVariantOptions = await selects
      .nth(1)
      .locator("option")
      .count();
    if (hasVariantOptions > 0) {
      await selects.nth(1).selectOption({ index: 0 });
    }
  }

  // Guest & booking fields (mevcut placeholder ve tiplere göre)
  const requiredTextInputs = page.locator('.fixed input[required][type="text"]');
  await requiredTextInputs.first().fill("Playwright Guest");

  const dateInputs = page.locator('.fixed input[type="date"]');
  await dateInputs.nth(0).fill("2026-01-10");

  const paxInput = page.locator('.fixed input[type="number"]').first();
  await paxInput.fill("2");

  // Kaydet
  await Promise.all([
    page.waitForURL(/\/app\/agency\/catalog\/bookings\//, { timeout: 30_000 }),
    page.click('.fixed button:has-text("Oluştur")'),
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
