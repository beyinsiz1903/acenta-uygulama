// tests/partner/partner-discovery.spec.ts
import { test, expect } from "./fixtures";

// Not: Bu test UI davranışını doğrular; gerçek davet gönderme akışını
// backend'e bağımlı olmadan sadece modal açılana kadar test ediyor.

test("Partner Keşfet sayfası min 2 karakter kuralı ve modal açılması", async ({ page }) => {
  await page.goto("/app/partners/discovery");

  // Başlık ve açıklama
  await expect(page.getByRole("heading", { name: "Partner Keşfet", exact: false })).toBeVisible();
  await expect(page.getByPlaceholder("Tenant ara (slug veya isim)…")).toBeVisible();

  const searchInput = page.getByPlaceholder("Tenant ara (slug veya isim)…");

  // < 2 karakter: uyarı metni görünür, sonuç listesi yok
  await searchInput.fill("a");
  await page.waitForTimeout(500); // debounce sonrasını bekle

  await expect(page.getByText("Arama için en az 2 karakter girin.")).toBeVisible();

  // 2+ karakter: en azından "Sonuç bulunamadı." veya sonuç listesi beklenir
  await searchInput.fill("de");
  await page.waitForTimeout(600);

  // Backend duruma göre ya sonuç, ya da boş state gelir; ikisini de kabul ediyoruz.
  const noResult = page.getByText("Sonuç bulunamadı.");

  // Eğer sonuç geldiyse ilk satır için Davet Et butonunun görünür olmasını bekleyelim
  const inviteButton = page.getByRole("button", { name: "Davet Et" });

  // Soft assertion pattern: Önce 'Davet Et' butonu var mı diye kontrol et, yoksa sadece boş state'i doğrula.
  if (await inviteButton.count()) {
    await expect(inviteButton.first()).toBeVisible();

    // Davet Et tıklandığında modal açılmalı
    await inviteButton.first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText("Partner daveti gönder")).toBeVisible();
  } else {
    await expect(noResult).toBeVisible();
  }
});
