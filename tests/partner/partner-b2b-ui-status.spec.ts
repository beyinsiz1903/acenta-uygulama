// tests/partner/partner-b2b-ui-status.spec.ts
import { test, expect } from "@playwright/test";

// Bu smoke testi, B2B Ağ sayfasının temel iskeletinin agency kullanıcısı için
// render olup olmadığını doğrular. Data varlığını değil, sadece başlık ve
// ana bölümlerin görünürlüğünü kontrol eder.

const BASE_URL = "https://enterprise-ops-8.preview.emergentagent.com";

async function login(page, email: string, password: string) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[data-testid="login-email"]', email);
  await page.fill('[data-testid="login-password"]', password);
  await page.click('[data-testid="login-submit"]');
  await page.waitForURL(/\/app\//, { timeout: 60000 });
}

// 1️⃣ B2B Ağ iskeleti smoke testi
test("B2B Ağ sayfası agency kullanıcısı için temel iskeleti render eder", async ({ page }) => {
  // Login as agency user first
  await login(page, "agency1@acenta.test", "agency123");
  
  // 1) /app/partners/b2b sayfasına git
  await page.goto(`${BASE_URL}/app/partners/b2b`);

  // 2) Ana başlık ve mod toggle'ları
  await expect(page.getByRole("heading", { name: "B2B Ağ" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Satıcı" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sağlayıcı" })).toBeVisible();

  // Varsayılan mod Satıcı; Satıcı modunun ana bölümleri
  await expect(page.getByText("Müsait Listingler")).toBeVisible();
  await expect(page.getByText("Taleplerim")).toBeVisible();

  // 3) Sağlayıcı moduna geç ve bölümleri kontrol et
  await page.getByRole("button", { name: "Sağlayıcı" }).click();

  await expect(page.getByText("Listinglerim")).toBeVisible();
  await expect(page.getByText("Gelen Talepler")).toBeVisible();

  // 4) Opsiyonel: en az bir empty state metni görünüyor mu?
  const emptyTexts = [
    "Henüz müsait tur yok. Aktif partner ilişkiniz yoksa burada liste göremezsiniz.",
    "Henüz talep oluşturmadınız.",
    "Henüz tur listelemediniz. \"Yeni Listing\" ile başlayın.",
    "Henüz gelen talep yok.",
  ];

  const emptyVisible = await Promise.any(
    emptyTexts.map(async (txt) => {
      const loc = page.getByText(txt);
      try {
        await expect(loc).toBeVisible({ timeout: 1000 });
        return true;
      } catch {
        return false;
      }
    }),
  ).catch(() => false);

  // Smoke için opsiyonel; görünmese bile test fail olmasın diye sadece logluyoruz
  if (!emptyVisible) {
    console.warn("[B2B UI Smoke] Empty state copy'lerinden hiçbiri görünmedi. Bu bekleniyor olabilir (seed'e bağlı)." );
  }
});
