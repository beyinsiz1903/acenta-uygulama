import { test, expect, Page } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
const AGENCY_EMAIL = process.env.AGENCY_EMAIL || "agency@example.com";
const AGENCY_PASSWORD = process.env.AGENCY_PASSWORD || "password";
const TEST_BOOKING_ID = process.env.TEST_CONFIRMED_BOOKING_ID;

async function loginAsAgency(page: Page) {
  await page.goto(`${BASE_URL}/login`);

  await page.getByTestId("login-email-input").fill(AGENCY_EMAIL);
  await page.getByTestId("login-password-input").fill(AGENCY_PASSWORD);
  await page.getByTestId("login-submit-button").click();

  await page.waitForURL("**/app/agency/**", { timeout: 15_000 });
}

async function readClipboardBestEffort(page: Page) {
  try {
    return await page.evaluate(async () => {
      if (!navigator.clipboard?.readText) return "";
      return await navigator.clipboard.readText();
    });
  } catch {
    return "";
  }
}

test.describe("AgencyHotelSearchPage smoke", () => {
  test("room-type-select görünür ve seçenekler listeleniyor", async ({ page }) => {
    await loginAsAgency(page);

    const SEARCH_URL = process.env.TEST_HOTEL_SEARCH_URL;
    test.skip(!SEARCH_URL, "TEST_HOTEL_SEARCH_URL env yok");

    await page.goto(`${BASE_URL}${SEARCH_URL}`);

    const roomType = page.getByTestId("room-type-select");
    await expect(roomType).toBeVisible();

    // Shadcn Select: trigger'a basınca role=option'lar listelenmeli
    await roomType.click();

    const optionsCount = await page.getByRole("option").count();
    expect(optionsCount).toBeGreaterThan(0);

    // pax warning: smoke seviyesinde default durumda yok olmalı
    await expect(page.getByTestId("pax-max-occupancy-warning")).toHaveCount(0);
  });
});

test.describe("AgencyBookingConfirmedPage smoke", () => {
  test("booking banner + copy + note + whatsapp", async ({ page, context }) => {
    test.skip(!TEST_BOOKING_ID, "TEST_CONFIRMED_BOOKING_ID env yok");

    await loginAsAgency(page);

    await page.goto(`${BASE_URL}/app/agency/booking/confirmed/${TEST_BOOKING_ID}`);

    const banner = page.getByTestId("booking-id-banner");
    await expect(banner).toBeVisible();

    const idCopyBtn = page.getByTestId("booking-id-copy");
    const summaryCopyBtn = page.getByTestId("booking-summary-copy");

    await expect(idCopyBtn).toBeEnabled();
    await expect(summaryCopyBtn).toBeEnabled();

    // ID copy -> sadece ID butonu "Kopyalandı"
    await idCopyBtn.click();
    await expect(idCopyBtn).toHaveText(/Kopyalandı/i);
    await expect(summaryCopyBtn).toHaveText(/Özeti Kopyala/i);

    const idClip = await readClipboardBestEffort(page);
    if (idClip) expect(idClip.length).toBeGreaterThan(0);

    // Summary copy -> sadece summary "Kopyalandı"
    await summaryCopyBtn.click();
    await expect(summaryCopyBtn).toHaveText(/Kopyalandı/i);

    const sumClip = await readClipboardBestEffort(page);
    if (sumClip) expect(sumClip).toMatch(/✅ Rezervasyon Özeti/);

    // Note input + clear
    const noteInput = page.getByTestId("hotel-note-input");
    const noteClear = page.getByTestId("hotel-note-clear");
    const whatsappBtn = page.getByTestId("whatsapp-send");

    await expect(noteInput).toBeVisible();
    await expect(noteClear).toBeDisabled();

    const noteText = "Geç giriş, bebek beşiği talebi.";
    await noteInput.fill(noteText);
    await expect(noteClear).toBeEnabled();

    // Summary -> Not satırı (clipboard okunabiliyorsa)
    await summaryCopyBtn.click();
    const sumWithNote = await readClipboardBestEffort(page);
    if (sumWithNote) expect(sumWithNote).toMatch(/Not:\s*Geç giriş, bebek beşiği talebi\./);

    // WhatsApp: yeni sayfa açılır; URL içinde text olmalı
    const [waPage] = await Promise.all([
      context.waitForEvent("page"),
      whatsappBtn.click(),
    ]);
    await waPage.waitForLoadState("domcontentloaded");

    const waUrl = waPage.url();
    expect(waUrl).toContain("wa.me");

    const decoded = decodeURIComponent(waUrl);
    expect(decoded).toMatch(/✅ Rezervasyon Talebi/);
    expect(decoded).toMatch(/Referans:/);
    expect(decoded).toMatch(/Not:\s*Geç giriş, bebek beşiği talebi\./);

    await waPage.close();

    // Clear -> input empty, refresh empty (localStorage remove)
    await noteClear.click();
    await expect(noteInput).toHaveValue("");
    await expect(noteClear).toBeDisabled();

    await page.reload();
    await expect(page.getByTestId("hotel-note-input")).toHaveValue("");
  });
});


test.describe("HotelBookingsPage smoke", () => {
  test("hotel banner + note input/clear + summary copy", async ({ page }) => {
    const TEST_HOTEL_BOOKINGS_URL = process.env.TEST_HOTEL_BOOKINGS_URL;
    if (!TEST_HOTEL_BOOKINGS_URL) test.skip();

    await loginAsAgency(page); // Eğer ayrı hotel user gerekiyorsa loginAsHotel'a alınabilir.

    await page.goto(`${BASE_URL}${TEST_HOTEL_BOOKINGS_URL}`);

    // 1) Listeden bir satır seç (banner için selectedForHeader set edilmeli)
    const rows = page.locator("tbody tr");
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(0);

    // Header satırını atlamak için tbody kullanıyoruz; ilk satırı tıkla
    await rows.first().click();

    // 2) Banner görünür olmalı (hotel prefix'li)
    const banner = page.getByTestId("hotel-booking-id-banner");
    await expect(banner).toBeVisible({ timeout: 15_000 });

    const idCopy = page.getByTestId("hotel-booking-id-copy");
    const summaryCopy = page.getByTestId("hotel-booking-summary-copy");

    await expect(idCopy).toBeEnabled();
    await expect(summaryCopy).toBeEnabled();

    // 3) Not alanı + temizle
    const noteInput = page.getByTestId("hotel-pending-note-input");
    const noteClear = page.getByTestId("hotel-pending-note-clear");

    await expect(noteInput).toBeVisible();
    await expect(noteClear).toBeDisabled();

    const noteText = "Overbooking riski, kapasite kontrolü rica.";
    await noteInput.fill(noteText);
    await expect(noteClear).toBeEnabled();

    // 4) Özeti Kopyala -> Not satırı (clipboard okunabiliyorsa)
    await summaryCopy.click();
    await expect(summaryCopy).toHaveText(/Kopyalandı/i);

    const summaryClipboard = await readClipboardBestEffort(page);
    if (summaryClipboard) {
      expect(summaryClipboard).toMatch(/✅ Rezervasyon Özeti/);
      expect(summaryClipboard).toMatch(/Not:\s*Overbooking riski/);
    }

    // 5) Temizle -> textarea boş, refresh sonrası da boş (localStorage temiz)
    await noteClear.click();
    await expect(noteInput).toHaveValue("");
    await expect(noteClear).toBeDisabled();

    await page.reload();
    await expect(page.getByTestId("hotel-pending-note-input")).toHaveValue("");
  });
});

