// frontend/tests/tour-booking-detail.spec.js
import { test, expect } from "@playwright/test";

const BASE_URL = process.env.PW_BASE_URL || "http://localhost:3000";

// İstersen env ile override edebilirsin:
// PW_AGENCY_EMAIL=agency1@demo.test
// PW_AGENCY_PASSWORD=agency123
const AGENCY_EMAIL = process.env.PW_AGENCY_EMAIL || "agency1@demo.test";
const AGENCY_PASSWORD = process.env.PW_AGENCY_PASSWORD || "agency123";

function uid() {
  return `PW-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

async function loginAsAgency(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: "domcontentloaded" });

  // Email
  const emailInput = page
    .locator("#email")
    .or(page.locator('input[type="email"]').first())
    .or(page.getByLabel(/e-?posta|email/i).first());
  await expect(emailInput).toBeVisible({ timeout: 15000 });
  await emailInput.fill(AGENCY_EMAIL);

  // Password
  const passInput = page
    .locator("#password")
    .or(page.locator('input[type="password"]').first())
    .or(page.getByLabel(/şifre|password/i).first());
  await expect(passInput).toBeVisible({ timeout: 15000 });
  await passInput.fill(AGENCY_PASSWORD);

  // Submit
  const submitBtn = page
    .getByRole("button", { name: /giriş|login|oturum aç/i })
    .first()
    .or(page.locator('button[type="submit"]').first());
  await expect(submitBtn).toBeVisible();
  await submitBtn.click();

  // Agency panel geldi mi?
  await page.waitForURL(/\/app\/agency\//, { timeout: 20000 });
}

async function openFirstBookingDetail(page) {
  await page.goto(`${BASE_URL}/app/agency/tour-bookings`, { waitUntil: "domcontentloaded" });

  // Liste sayfası geldi mi?
  await expect(page.getByText(/tur rezervasyon talepleri/i)).toBeVisible({ timeout: 15000 });

  // İlk kartın detayına git:
  // 1) Eğer kartın içinde detay linki varsa:
  const detailLink = page.locator('a[href^="/app/agency/tour-bookings/"]').first();
  if (await detailLink.count()) {
    await detailLink.click();
    await page.waitForURL(/\/app\/agency\/tour-bookings\/[^/]+$/, { timeout: 15000 });
    return;
  }

  // 2) Yoksa kartı tıklanabilir varsay (ilk kart container)
  const firstCard = page.locator('[data-testid="tour-booking-card"]').first();
  if (await firstCard.count()) {
    await firstCard.click();
    await page.waitForURL(/\/app\/agency\/tour-bookings\/[^/]+$/, { timeout: 15000 });
    return;
  }

  // 3) Son çare: listede ilk "Onayla/Reddet" butonuna yakın bir kartı yakala ve parent click dene
  const anyRow = page.getByRole("button", { name: /onayla|reddet/i }).first();
  await expect(anyRow).toBeVisible({ timeout: 15000 });

  // Butonun üst parent’ını tıklamayı dene (DOM’a göre değişebilir)
  const parentClickable = anyRow.locator("xpath=ancestor::*[self::a or self::div][1]");
  await parentClickable.click({ force: true });
  await page.waitForURL(/\/app\/agency\/tour-bookings\/[^/]+$/, { timeout: 15000 });
}

test.describe("C3 - Tour booking detail E2E", () => {
  test("list -> detail -> tel link -> add note -> empty note -> approve (if available) -> offline payment (if available)", async ({ page }) => {
    // 1) Login
    await loginAsAgency(page);

    // 2) Liste -> detay
    await openFirstBookingDetail(page);

    // Detay sayfası temel başlıklar (en azından tur adı / status vs.)
    // Tur adı genelde görünür; yoksa sayfa yine de render olmalı.
    await expect(page.locator("body")).toContainText(/tur|rezervasyon|talep/i);

    // 3) tel: link kontrolü
    const telLink = page.locator('a[href^="tel:"]').first();
    await expect(telLink).toBeVisible({ timeout: 10000 });
    const href = await telLink.getAttribute("href");
    expect(href).toBeTruthy();
    expect(href.startsWith("tel:")).toBeTruthy();

    // 4) İç not ekleme (unique)
    const noteText = `E2E note ${uid()}`;

    // textarea/input bul (fallback’li)
    const noteBox = page.locator('textarea[placeholder*="not" i]').first();

    await expect(noteBox).toBeVisible({ timeout: 10000 });
    await noteBox.fill(noteText);

    const addNoteBtn = page.getByRole("button", { name: /not ekle|kaydet|ekle/i }).first();

    await expect(addNoteBtn).toBeVisible();
    await addNoteBtn.click();

    // Toast / ekranda notun görünmesini bekle (toast metni değişebilir diye iki türlü doğruluyoruz)
    // 1) Not metni sayfada görünür olmalı (liste/history render ediliyorsa)
    await expect(page.locator("body")).toContainText(noteText, { timeout: 15000 });

    // 5) Boş not denemesi (UI validasyon/toast)
    await noteBox.fill("");
    await addNoteBtn.click();

    // Boş notta hata toast’u/metni: (metin değişebilir, genel bir eşleşme)
    // Sonner toast genelde body içinde görünür bir text basar.
    await expect(page.locator("body")).toContainText(/not.*(boş|doldur|zorunlu)|lütfen.*not/i, { timeout: 8000 });

    // 6) Status Onayla (buton varsa)
    const approveBtn = page.getByRole("button", { name: /onayla/i }).first();
    if (await approveBtn.count()) {
      page.once("dialog", async (dialog) => {
        await dialog.accept();
      });

      await approveBtn.click();

      // Sonrasında status değişti mi? (badge text)
      await expect(page.locator("body")).toContainText(/onaylandı|approved/i, { timeout: 15000 });
    }

    // 7) Offline ödeme kartı ve kopyala aksiyonları (varsa)
    const prepareBtn = page.locator('[data-testid="btn-prepare-offline-payment"]').first();
    const offlineCard = page.locator('[data-testid="offline-payment-card"]').first();

    if (await prepareBtn.count()) {
      await prepareBtn.click();
      await expect(page.locator("body")).toContainText(/offline ödeme talimatı hazırlandı/i, {
        timeout: 15000,
      });
    }

    if (await offlineCard.count()) {
      // Kart içi butonlar
      const copyIban = page.locator('[data-testid="btn-copy-iban"]').first();
      const copyRef = page.locator('[data-testid="btn-copy-reference"]').first();
      const copyNote = page.locator('[data-testid="btn-copy-payment-note"]').first();

      // IBAN kopyala
      if (await copyIban.count()) {
        await copyIban.click();
        await expect(page.locator("body")).toContainText(/IBAN.*panoya kopyalandı/i, {
          timeout: 8000,
        });
      }

      // Referans kodu kopyala
      if (await copyRef.count()) {
        await copyRef.click();
        await expect(page.locator("body")).toContainText(/Referans kodu.*panoya kopyalandı/i, {
          timeout: 8000,
        });
      }

      // Ödeme açıklaması kopyala
      if (await copyNote.count()) {
        await copyNote.click();
        await expect(page.locator("body")).toContainText(/Ödeme açıklaması.*panoya kopyalandı/i, {
          timeout: 8000,
        });
      }
    }

    // Son sanity: sayfa crash olmadı
    await expect(page.locator("body")).toBeVisible();
  });
});
