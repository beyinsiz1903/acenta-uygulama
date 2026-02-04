// tests/partner/partner-relationships.spec.ts
import { test, expect } from "./fixtures";

// Basit smoke test: Partner İlişkileri sayfası yüklenebiliyor mu?
test("Partner İlişkileri sayfası açılır ve filtreler görünür", async ({ page }) => {
  await page.goto("/app/partners/relationships");

  await expect(
    page.getByRole("heading", { name: "Partner İlişkileri", exact: false })
  ).toBeVisible();

  await expect(page.getByText("Filtreler")).toBeVisible();
  await expect(page.getByText("Durum")).toBeVisible();
  await expect(page.getByText("Rol")).toBeVisible();

  await expect(page.getByText("İlişki listesi")).toBeVisible();
});
