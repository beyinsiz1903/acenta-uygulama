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


test.describe("AgencyBookingNewPage FAZ-8 smoke", () => {
  test("wizard pending/confirmed buttons and shortcut hint are visible", async ({ page }) => {
    const TEST_BOOKING_WIZARD_URL = process.env.TEST_BOOKING_WIZARD_URL;
    if (!TEST_BOOKING_WIZARD_URL) test.skip();

    await loginAsAgency(page);

    await page.goto(`${BASE_URL}${TEST_BOOKING_WIZARD_URL}`);

    const pendingBtn = page.getByTestId("wizard-submit-pending");
    const confirmedBtn = page.getByTestId("wizard-submit-confirmed");
    const shortcutHint = page.getByTestId("booking-wizard-shortcut-hint");

    await expect(pendingBtn).toBeVisible();
    await expect(confirmedBtn).toBeVisible();
    await expect(shortcutHint).toBeVisible();

    await expect(pendingBtn).toBeEnabled();
    await expect(confirmedBtn).toBeEnabled();
  });
});


test.describe("AgencyBookingNewPage FAZ-8.2 mocked submit wiring", () => {
  test("8.2-A: pending button → draft + submit API calls", async ({ page }) => {
    const TEST_BOOKING_WIZARD_URL = process.env.TEST_BOOKING_WIZARD_URL;
    if (!TEST_BOOKING_WIZARD_URL) test.skip();

    await loginAsAgency(page);

    // Mock draft creation
    const mockDraftId = "draft-mock-001";
    let draftCalled = false;
    await page.route("**/api/agency/bookings/draft", async (route) => {
      draftCalled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          draft_id: mockDraftId,
          hotel_id: "hotel-001",
          search_id: "search-001",
        }),
      });
    });

    // Mock submit (pending)
    const mockPendingBookingId = "pending-mock-001";
    let submitCalled = false;
    await page.route("**/api/agency/bookings/*/submit", async (route) => {
      submitCalled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          booking_id: mockPendingBookingId,
          status: "pending",
          code: "PND-12345",
        }),
      });
    });

    await page.goto(`${BASE_URL}${TEST_BOOKING_WIZARD_URL}`);

    const pendingBtn = page.getByTestId("wizard-submit-pending");
    await expect(pendingBtn).toBeVisible();

    // Click pending button
    await pendingBtn.click();

    // Assert: both APIs should be called
    await page.waitForTimeout(1000); // Give time for API calls
    expect(draftCalled).toBe(true);
    expect(submitCalled).toBe(true);
  });

  test("8.2-A: confirmed button → only draft API call", async ({ page }) => {
    const TEST_BOOKING_WIZARD_URL = process.env.TEST_BOOKING_WIZARD_URL;
    if (!TEST_BOOKING_WIZARD_URL) test.skip();

    await loginAsAgency(page);

    // Mock draft creation
    const mockDraftId = "draft-mock-002";
    let draftCalled = false;
    await page.route("**/api/agency/bookings/draft", async (route) => {
      draftCalled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          draft_id: mockDraftId,
          hotel_id: "hotel-001",
          search_id: "search-001",
        }),
      });
    });

    // Mock submit (should NOT be called for confirmed)
    let submitCalled = false;
    await page.route("**/api/agency/bookings/*/submit", async (route) => {
      submitCalled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto(`${BASE_URL}${TEST_BOOKING_WIZARD_URL}`);

    const confirmedBtn = page.getByTestId("wizard-submit-confirmed");
    await expect(confirmedBtn).toBeVisible();

    // Click confirmed button
    await confirmedBtn.click();

    // Assert: only draft should be called
    await page.waitForTimeout(1000);
    expect(draftCalled).toBe(true);
    expect(submitCalled).toBe(false);
  });

  test("8.2-B: pending button → navigates to /app/agency/booking/pending/:id", async ({ page }) => {
    const TEST_BOOKING_WIZARD_URL = process.env.TEST_BOOKING_WIZARD_URL;
    if (!TEST_BOOKING_WIZARD_URL) test.skip();

    await loginAsAgency(page);

    const mockDraftId = "draft-mock-003";
    const mockPendingBookingId = "pending-mock-003";

    // Mock draft
    await page.route("**/api/agency/bookings/draft", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          draft_id: mockDraftId,
          hotel_id: "hotel-001",
          search_id: "search-001",
        }),
      });
    });

    // Mock submit
    await page.route("**/api/agency/bookings/*/submit", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          booking_id: mockPendingBookingId,
          status: "pending",
          code: "PND-12345",
        }),
      });
    });

    await page.goto(`${BASE_URL}${TEST_BOOKING_WIZARD_URL}`);

    const pendingBtn = page.getByTestId("wizard-submit-pending");
    await pendingBtn.click();

    // Assert: should navigate to pending page
    await expect(page).toHaveURL(
      new RegExp(`/app/agency/booking/pending/${mockPendingBookingId}`),
      { timeout: 10_000 }
    );
  });

  test("8.2-B: confirmed button → navigates to /app/agency/booking/draft/:id", async ({ page }) => {
    const TEST_BOOKING_WIZARD_URL = process.env.TEST_BOOKING_WIZARD_URL;
    if (!TEST_BOOKING_WIZARD_URL) test.skip();

    await loginAsAgency(page);

    const mockDraftId = "draft-mock-004";

    // Mock draft
    await page.route("**/api/agency/bookings/draft", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          draft_id: mockDraftId,
          hotel_id: "hotel-001",
          search_id: "search-001",
        }),
      });
    });

    await page.goto(`${BASE_URL}${TEST_BOOKING_WIZARD_URL}`);

    const confirmedBtn = page.getByTestId("wizard-submit-confirmed");
    await confirmedBtn.click();

    // Assert: should navigate to draft page
    await expect(page).toHaveURL(
      new RegExp(`/app/agency/booking/draft/${mockDraftId}`),
      { timeout: 10_000 }
    );
  });

  test("8.2-C: loading state shows on correct button (pending)", async ({ page }) => {
    const TEST_BOOKING_WIZARD_URL = process.env.TEST_BOOKING_WIZARD_URL;
    if (!TEST_BOOKING_WIZARD_URL) test.skip();

    await loginAsAgency(page);

    // Mock draft with delay
    await page.route("**/api/agency/bookings/draft", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          draft_id: "draft-mock-005",
          hotel_id: "hotel-001",
          search_id: "search-001",
        }),
      });
    });

    // Mock submit with delay
    await page.route("**/api/agency/bookings/*/submit", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          booking_id: "pending-mock-005",
          status: "pending",
          code: "PND-12345",
        }),
      });
    });

    await page.goto(`${BASE_URL}${TEST_BOOKING_WIZARD_URL}`);

    const pendingBtn = page.getByTestId("wizard-submit-pending");
    const confirmedBtn = page.getByTestId("wizard-submit-confirmed");

    // Click pending button
    const clickPromise = pendingBtn.click();

    // During loading: pending should be disabled, confirmed should remain enabled
    await page.waitForTimeout(200);
    await expect(pendingBtn).toBeDisabled();
    await expect(confirmedBtn).toBeEnabled();

    // Wait for completion
    await clickPromise;
  });

  test("8.2-C: loading state shows on correct button (confirmed)", async ({ page }) => {
    const TEST_BOOKING_WIZARD_URL = process.env.TEST_BOOKING_WIZARD_URL;
    if (!TEST_BOOKING_WIZARD_URL) test.skip();

    await loginAsAgency(page);

    // Mock draft with delay
    await page.route("**/api/agency/bookings/draft", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          draft_id: "draft-mock-006",
          hotel_id: "hotel-001",
          search_id: "search-001",
        }),
      });
    });

    await page.goto(`${BASE_URL}${TEST_BOOKING_WIZARD_URL}`);

    const pendingBtn = page.getByTestId("wizard-submit-pending");
    const confirmedBtn = page.getByTestId("wizard-submit-confirmed");

    // Click confirmed button
    const clickPromise = confirmedBtn.click();

    // During loading: confirmed should be disabled, pending should remain enabled
    await page.waitForTimeout(200);
    await expect(confirmedBtn).toBeDisabled();
    await expect(pendingBtn).toBeEnabled();

    // Wait for completion
    await clickPromise;
  });
});


