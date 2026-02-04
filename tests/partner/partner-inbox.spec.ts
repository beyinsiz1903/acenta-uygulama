// tests/partner/partner-inbox.spec.ts
import { test, expect } from "./fixtures";

// Basit smoke test: Partner Gelen Kutusu sayfası yüklenebiliyor mu?
test("Partner Inbox açılır ve sayfa iskeleti görünür", async ({ page }) => {
  await page.goto("/app/partners/inbox");

  await expect(
    page.getByRole("heading", { name: "Partner Gelen Kutusu", exact: false })
  ).toBeVisible();

  await expect(page.getByText("Gelen Davetler")).toBeVisible();
  await expect(page.getByText("Gönderilen Davetler")).toBeVisible();
});
