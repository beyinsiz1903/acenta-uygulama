// tests/partner/partner-subnav-navigation.spec.ts
import { test, expect } from "./fixtures";

// Subnav üzerinden temel navigasyon smoke test'leri
test("Partner subnav ile Davetler ve Mutabakat sayfalarına geçiş", async ({ page }) => {
  await page.goto("/app/partners");

  // Davetler sekmesine tıkla
  await page.getByRole("link", { name: "Davetler" }).click();
  await expect(page).toHaveURL(/\/app\/partners\/invites/);
  await expect(page.getByText("Davet listesi")).toBeVisible();

  // Mutabakat sekmesine tıkla
  await page.getByRole("link", { name: "Mutabakat" }).click();
  await expect(page).toHaveURL(/\/app\/partners\/statements/);
  await expect(page.getByText("Mutabakat Ekstresi")).toBeVisible();
});
