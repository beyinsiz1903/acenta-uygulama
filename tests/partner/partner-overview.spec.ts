// tests/partner/partner-overview.spec.ts
import { test, expect } from "./fixtures";

// Basit smoke test: Partner Genel Bakış sayfası yüklenebiliyor mu?
test("Partner Genel Bakış açılır ve subnav görünür", async ({ page }) => {
  await page.goto("/app/partners");

  await expect(
    page.getByRole("heading", { name: "Partners  Genel Bakış", exact: false })
  ).toBeVisible();

  // Subnav sekmeleri
  await expect(page.getByRole("link", { name: "Genel Bakış" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Gelen Kutusu" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Davetler" })).toBeVisible();
  await expect(page.getByRole("link", { name: "İlişkiler" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Keşfet" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Mutabakat" })).toBeVisible();
});
