// frontend/tests/agency-catalog-products-bookings.spec.js

import { test, expect } from "@playwright/test";

async function loginAsAgency(page) {
  await page.goto("/login");
  await page.waitForLoadState('networkidle');
  await page.fill('[data-testid="login-email"]', "agency1@demo.test");
  await page.fill('[data-testid="login-password"]', "agency123");
  await page.click('[data-testid="login-submit"]');
  await expect(page).toHaveURL(/\/app\/agency/, { timeout: 15000 });
}

test("Catalog Products → Variants → Booking full flow", async ({ page }) => {
  // LOGIN
  await loginAsAgency(page);

  // PRODUCTS PAGE
  await page.goto("/app/agency/catalog/products");

  const productRows = page.locator('[data-testid="catalog-product-row"]');

  // Eğer hiç ürün yoksa basit bir ürün oluştur
  if ((await productRows.count()) === 0) {
    const createTitle = page.locator('[data-testid="catalog-product-title-input"]');
    await createTitle.fill("Test Katalog Turu");
    await page.click('[data-testid="btn-catalog-create-product"]');
    await expect(productRows.first()).toBeVisible({ timeout: 10000 });
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
    await expect(variantRows.first()).toBeVisible({ timeout: 10000 });
  }

  // BOOKINGS PAGE
  await page.goto("/app/agency/catalog/bookings");
  await page.click('[data-testid="btn-catalog-create-booking"]');

  // Ürün seç
  const productSelect = page.locator(".fixed [data-testid='select-product'] select");

  // Eğer data-testid ile select'leri bulamazsak form alan isimleriyle fallback yapacağız.
  // Basit yaklaşım: ilk select ürün, ikinci select variant olarak varsayılır.

  const selects = page.locator(".fixed select");
  const selectCount = await selects.count();

  if (selectCount >= 1) {
    await selects.nth(0).selectOption({ index: 0 });
  }
  if (selectCount >= 2) {
    // Variant seçmek opsiyonel, varsa ilkini seç
    const hasVariantOptions = await selects
      .nth(1)
      .locator("option")
      .count();
    if (hasVariantOptions > 0) {
      await selects.nth(1).selectOption({ index: 0 });
    }
  }

  // Guest & booking fields
  await page.fill('input[required][type="text"]', "Playwright Guest");
  const dateInputs = page.locator('.fixed input[type="date"]');
  await dateInputs.nth(0).fill("2026-01-10");

  const paxInput = page.locator('.fixed input[type="number"]').first();
  await paxInput.fill("2");

  // Kaydet
  await page.click('.fixed button:has-text("Oluştur")');

  // DETAIL PAGE
  await expect(page).toHaveURL(/\/app\/agency\/catalog\/bookings\//);

  // Internal note ekle
  await page.fill('[data-testid="internal-note-input"]', "Playwright test notu");
  await page.click('[data-testid="btn-add-internal-note"]');
  await expect(page.locator("text=Playwright test notu")).toBeVisible({ timeout: 10000 });

  // Approve butonu görünüyorsa onayla
  const approveBtn = page.locator('[data-testid="btn-catalog-approve"]');
  if (await approveBtn.isVisible()) {
    await approveBtn.click();
    await expect(page.locator("text=approved")).toBeVisible({ timeout: 10000 });
  }
});
