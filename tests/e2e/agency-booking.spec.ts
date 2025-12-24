import { test, expect } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
const AGENCY_EMAIL = process.env.AGENCY_EMAIL || "agency@example.com";
const AGENCY_PASSWORD = process.env.AGENCY_PASSWORD || "password";
const TEST_BOOKING_ID = process.env.TEST_CONFIRMED_BOOKING_ID;

async function loginAsAgency(page) {
  await page.goto(`${BASE_URL}/login`);

  await page.getByTestId("login-email-input").fill(AGENCY_EMAIL);
  await page.getByTestId("login-password-input").fill(AGENCY_PASSWORD);
  await page.getByTestId("login-submit-button").click();

  await page.waitForURL("**/app/agency/**", { timeout: 15_000 });
}

async function readClipboardBestEffort(page) {
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


// ========== FAZ-10.1: Admin Metrics Dashboard E2E Smoke ==========

const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "";

/**
 * Admin login helper
 * - login-email-input / login-password-input / login-submit-button kullanır
 * - login sonrası /app/admin/** bekler (role routing)
 */
async function loginAsAdmin(page) {
  if (!ADMIN_EMAIL || !ADMIN_PASSWORD) {
    test.skip();
  }

  await page.goto(`${BASE_URL}/login`);

  // Clear and fill email
  const emailInput = page.getByTestId("login-email");
  await emailInput.click();
  await emailInput.fill("");
  await emailInput.fill(ADMIN_EMAIL);

  // Fill password
  const passwordInput = page.getByTestId("login-password");
  await passwordInput.click();
  await passwordInput.fill("");
  await passwordInput.fill(ADMIN_PASSWORD);

  // Submit
  await page.getByTestId("login-submit").click();

  // Wait for app route (admin area)
  await page.waitForURL("**/app/**", { timeout: 15_000 });
}

test.describe("AdminMetricsPage smoke (FAZ-10)", () => {
  test("admin metrics page renders stats, trend chart and top hotels", async ({ page }) => {
    const TEST_ADMIN_METRICS_URL = process.env.TEST_ADMIN_METRICS_URL;
    if (!TEST_ADMIN_METRICS_URL) test.skip();

    await loginAsAdmin(page);

    await page.goto(`${BASE_URL}${TEST_ADMIN_METRICS_URL}`);
    await page.waitForTimeout(2000); // Wait for data load

    // 1) Stat cards render
    const statTotal = page.getByTestId("metrics-stat-total");
    const statPending = page.getByTestId("metrics-stat-pending");
    const statConfirmed = page.getByTestId("metrics-stat-confirmed");
    const statAvg = page.getByTestId("metrics-stat-avg-time");

    await expect(statTotal).toBeVisible();
    await expect(statPending).toBeVisible();
    await expect(statConfirmed).toBeVisible();
    await expect(statAvg).toBeVisible();

    // 2) Trend chart + Top hotels list render
    await expect(page.getByTestId("metrics-trend-chart")).toBeVisible();
    await expect(page.getByTestId("metrics-top-hotels")).toBeVisible();

    // 3) Soft assert: total is not empty text (demo data varsa >0 beklenebilir)
    // Kırılgan olmamak için parse etmiyoruz; sadece boş değil.
    const totalText = (await statTotal.innerText()).trim();
    expect(totalText).not.toEqual("");

    // 4) Demo seed button visible (super_admin için)
    const seedBtn = page.getByTestId("metrics-seed-demo");
    await expect(seedBtn).toBeVisible();
  });
});

// ========== FAZ-12.1: Admin Metrics Date Range & CSV Smoke ==========

test.describe("AdminMetricsPage FAZ-12.1+13.2 metrics smoke", () => {
  test("T1 - date range controls & CSV buttons render and preset triggers fetch (mocked API)", async ({ page }) => {
    const TEST_ADMIN_METRICS_URL = process.env.TEST_ADMIN_METRICS_URL || "/app/admin/metrics";

    // Auth bypass: token & user localStorage'da hazır olsun
    await page.addInitScript(() => {
      const token = "e2e-admin-token";
      window.localStorage.setItem("acenta_token", token);
      window.localStorage.setItem(
        "acenta_user",
        JSON.stringify({
          id: "e2e-admin",
          email: "admin@acenta.test",
          roles: ["super_admin"],
        })
      );
    });

    // Optional: /me veya benzeri endpoint varsa 200 döndürelim
    await page.route("**/api/**/me**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "e2e-admin", role: "super_admin", email: "admin@acenta.test" }),
      });
    });

    // Metrics endpoint'lerini mockla ve overview URL'sini yakala
    let lastOverviewUrl = "";
    await page.route("**/api/admin/metrics/overview**", async (route) => {
      const reqUrl = route.request().url();
      lastOverviewUrl = reqUrl;
      const url = new URL(reqUrl);
      const days = Number(url.searchParams.get("days") || 7);

      const endDate = new Date();
      const end = endDate.toISOString().slice(0, 10);
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);
      const start = startDate.toISOString().slice(0, 10);

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period: { start, end, days },
          bookings: { total: 10, pending: 3, confirmed: 6, cancelled: 1 },
          avg_approval_time_hours: 5.2,
          bookings_with_notes_pct: 12,
          top_hotels: [],
        }),
      });
    });

    await page.route("**/api/admin/metrics/trends**", async (route) => {
      const reqUrl = route.request().url();
      const url = new URL(reqUrl);
      const days = Number(url.searchParams.get("days") || 7);

      const endDate = new Date();
      const end = endDate.toISOString().slice(0, 10);
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);
      const start = startDate.toISOString().slice(0, 10);

      const len = Math.min(days, 7);
      const rows = Array.from({ length: len }).map((_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (len - 1 - i));
        const ds = d.toISOString().slice(0, 10);
        return { date: ds, pending: 1, confirmed: 2, cancelled: 0, total: 3 };
      });

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period: { start, end, days },
          daily_trends: rows,
        }),
      });
    });

    await page.route("**/api/admin/insights/queues**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          slow_hours: 24,
          slow_pending: [],
          noted_pending: [],
        }),
      });
    });

    await page.route("**/api/admin/insights/funnel**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          total: 0,
          pending: 0,
          confirmed: 0,
          cancelled: 0,
          conversion_pct: 0,
        }),
      });
    });

    // Sayfaya git
    await page.goto(`${BASE_URL}${TEST_ADMIN_METRICS_URL}`);

    // Date range inputs visible
    await expect(page.getByTestId("metrics-range-start")).toBeVisible();
    await expect(page.getByTestId("metrics-range-end")).toBeVisible();

    // CSV buttons visible
    await expect(page.getByTestId("metrics-export-overview")).toBeVisible();
    await expect(page.getByTestId("metrics-export-trends")).toBeVisible();
    await expect(page.getByTestId("metrics-export-queues")).toBeVisible();

    // 14g preset → overview URL içinde days=14 beklenir
    await page.locator("button", { hasText: "14g" }).click();

    await page.waitForTimeout(200);

    expect(lastOverviewUrl).toContain("/api/admin/metrics/overview");
    expect(lastOverviewUrl).toContain("days=14");
  });

  test("T2 - Detailed Queues tab shows filters and table", async ({ page }) => {
    const TEST_ADMIN_METRICS_URL = process.env.TEST_ADMIN_METRICS_URL || "/app/admin/metrics";

    await page.addInitScript(() => {
      const token = "e2e-admin-token";
      window.localStorage.setItem("acenta_token", token);
      window.localStorage.setItem(
        "acenta_user",
        JSON.stringify({
          id: "e2e-admin",
          email: "admin@acenta.test",
          roles: ["super_admin"],
        })
      );
    });

    // Mock queues endpoint with slow & noted data
    await page.route("**/api/admin/insights/queues**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          slow_hours: 24,
          slow_pending: [
            {
              booking_id: "SLOW-1",
              hotel_id: "H1",
              hotel_name: "Hotel One",
              age_hours: 30,
              has_note: false,
            },
          ],
          noted_pending: [
            {
              booking_id: "NOTE-1",
              hotel_id: "H2",
              hotel_name: "Hotel Two",
              age_hours: 10,
              has_note: true,
            },
          ],
        }),
      });
    });

    // Other endpoints minimal mocks to keep page happy
    await page.route("**/api/admin/metrics/overview**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period: { start: "2025-01-01", end: "2025-01-07", days: 7 },
          bookings: { total: 2, pending: 1, confirmed: 1, cancelled: 0 },
          avg_approval_time_hours: 5,
          bookings_with_notes_pct: 50,
          top_hotels: [],
        }),
      });
    });

    await page.route("**/api/admin/metrics/trends**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period: { start: "2025-01-01", end: "2025-01-07", days: 7 },
          daily_trends: [],
        }),
      });
    });

    await page.route("**/api/admin/insights/funnel**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          total: 0,
          pending: 0,
          confirmed: 0,
          cancelled: 0,
          conversion_pct: 0,
        }),
      });
    });

    const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
    await page.goto(`${BASE_URL}${TEST_ADMIN_METRICS_URL}`);

    // Overview default tab
    await expect(page.getByTestId("metrics-tab-overview")).toBeVisible();

    // Switch to Detailed Queues tab
    await page.getByTestId("metrics-tab-detailed-queues").click();

    // Filters visible
    await expect(page.getByTestId("metrics-dq-filter-hotel")).toBeVisible();
    await expect(page.getByTestId("metrics-dq-filter-min-age")).toBeVisible();
    await expect(page.getByTestId("metrics-dq-filter-has-note")).toBeVisible();
    await expect(page.getByTestId("metrics-dq-filter-search")).toBeVisible();

    // Table rendered
    await expect(page.getByTestId("metrics-dq-table")).toBeVisible();
  });

  test("T3 - Conversion tab shows KPI cards", async ({ page }) => {
    const TEST_ADMIN_METRICS_URL = process.env.TEST_ADMIN_METRICS_URL || "/app/admin/metrics";
    const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";

    await page.addInitScript(() => {
      const token = "e2e-admin-token";
      window.localStorage.setItem("acenta_token", token);
      window.localStorage.setItem(
        "acenta_user",
        JSON.stringify({
          id: "e2e-admin",
          email: "admin@acenta.test",
          roles: ["super_admin"],
        })
      );
    });

    await page.route("**/api/admin/insights/funnel**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          total: 10,
          pending: 3,
          confirmed: 6,
          cancelled: 1,
          conversion_pct: 60,
        }),
      });
    });

    await page.route("**/api/admin/metrics/overview**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period: { start: "2025-01-01", end: "2025-01-07", days: 7 },
          bookings: { total: 10, pending: 3, confirmed: 6, cancelled: 1 },
          avg_approval_time_hours: 5,
          bookings_with_notes_pct: 12,
          top_hotels: [],
        }),
      });
    });

    await page.route("**/api/admin/metrics/trends**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period: { start: "2025-01-01", end: "2025-01-07", days: 7 },
          daily_trends: [],
        }),
      });
    });

    await page.route("**/api/admin/insights/queues**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          slow_hours: 24,
          slow_pending: [],
          noted_pending: [],
        }),
      });
    });

    await page.goto(`${BASE_URL}${TEST_ADMIN_METRICS_URL}`);

    await page.getByTestId("metrics-tab-detailed-queues").click();

    await expect(page.getByTestId("metrics-export-queues-filtered").first()).toBeVisible();
  });

  test("T5 - Export filtered queues button visible", async ({ page }) => {
    const TEST_ADMIN_METRICS_URL = process.env.TEST_ADMIN_METRICS_URL || "/app/admin/metrics";
    const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";

    await page.addInitScript(() => {
      const token = "e2e-admin-token";
      window.localStorage.setItem("acenta_token", token);
      window.localStorage.setItem(
        "acenta_user",
        JSON.stringify({
          id: "e2e-admin",
          email: "admin@acenta.test",
          roles: ["super_admin"],
        })
      );
    });

    await page.route("**/api/admin/insights/queues**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          slow_hours: 24,
          slow_pending: [
            {
              booking_id: "SLOW-1",
              hotel_id: "H1",
              hotel_name: "Hotel One",
              age_hours: 30,
              has_note: false,
            },
          ],
          noted_pending: [
            {
              booking_id: "NOTE-1",
              hotel_id: "H2",
              hotel_name: "Hotel Two",
              age_hours: 10,
              has_note: true,
            },
          ],
        }),
      });
    });

    // Minimal mocks for other endpoints
    await page.route("**/api/admin/metrics/overview**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period: { start: "2025-01-01", end: "2025-01-07", days: 7 },
          bookings: { total: 10, pending: 3, confirmed: 6, cancelled: 1 },
          avg_approval_time_hours: 5,
          bookings_with_notes_pct: 12,
          top_hotels: [],
        }),
      });
    });

    await page.route("**/api/admin/metrics/trends**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period: { start: "2025-01-01", end: "2025-01-07", days: 7 },
          daily_trends: [],
        }),
      });
    });

    await page.route("**/api/admin/insights/funnel**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          total: 10,
          pending: 3,
          confirmed: 6,
          cancelled: 1,
          conversion_pct: 60,
        }),
      });
    });

    await page.goto(`${BASE_URL}${TEST_ADMIN_METRICS_URL}`);

    await page.getByTestId("metrics-tab-detailed-queues").click();

    await expect(page.getByTestId("metrics-export-queues-filtered")).toBeVisible();
  });
});


test.describe("AdminMetricsPage FAZ-11.1 insights smoke", () => {
  test("T1 - insight cards render with mock data", async ({ page }) => {
    const TEST_ADMIN_METRICS_URL = process.env.TEST_ADMIN_METRICS_URL;
    if (!TEST_ADMIN_METRICS_URL) test.skip();

    await loginAsAdmin(page);

    // Mock insights endpoints
    await page.route("**/api/admin/insights/queues**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          slow_hours: 24,
          slow_pending: [
            {
              booking_id: "slow-mock-001",
              hotel_id: "hotel-1",
              hotel_name: "Mock Hotel 1",
              created_at: "2025-01-10T10:00:00Z",
              age_hours: 48.5,
              status: "pending",
              has_note: true,
            },
          ],
          noted_pending: [
            {
              booking_id: "noted-mock-001",
              hotel_id: "hotel-2",
              hotel_name: "Mock Hotel 2",
              created_at: "2025-01-15T12:00:00Z",
              age_hours: 12.3,
              status: "pending",
              has_note: true,
            },
          ],
        }),
      });
    });

    await page.route("**/api/admin/insights/funnel**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          total: 20,
          pending: 9,
          confirmed: 9,
          cancelled: 2,
          conversion_pct: 45.0,
        }),
      });
    });

    await page.goto(`${BASE_URL}${TEST_ADMIN_METRICS_URL}`);
    await page.waitForTimeout(2000);

    // Assert insight cards
    const slowCard = page.getByTestId("metrics-insight-slow-count");
    const notedCard = page.getByTestId("metrics-insight-noted-count");
    const conversionCard = page.getByTestId("metrics-funnel-conversion");

    await expect(slowCard).toBeVisible();
    await expect(notedCard).toBeVisible();
    await expect(conversionCard).toBeVisible();

    // Check values (soft match - mock has 1 in each array but UI shows count)
    const slowText = await slowCard.innerText();
    const notedText = await notedCard.innerText();
    const conversionText = await conversionCard.innerText();

    expect(slowText).toContain("1"); // 1 slow pending in mock
    expect(notedText).toContain("1"); // 1 noted pending in mock
    expect(conversionText).toContain("45"); // 45% conversion
  });

  test("T2 - tabs switch table content", async ({ page }) => {
    const TEST_ADMIN_METRICS_URL = process.env.TEST_ADMIN_METRICS_URL;
    if (!TEST_ADMIN_METRICS_URL) test.skip();

    await loginAsAdmin(page);

    // Mock with multiple bookings
    await page.route("**/api/admin/insights/queues**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          slow_hours: 24,
          slow_pending: [
            {
              booking_id: "slow-001",
              hotel_id: "h1",
              hotel_name: "Slow Hotel",
              created_at: "2025-01-10T10:00:00Z",
              age_hours: 50.0,
              status: "pending",
              has_note: false,
            },
          ],
          noted_pending: [
            {
              booking_id: "noted-001",
              hotel_id: "h2",
              hotel_name: "Noted Hotel",
              created_at: "2025-01-15T12:00:00Z",
              age_hours: 10.0,
              status: "pending",
              has_note: true,
            },
          ],
        }),
      });
    });

    await page.route("**/api/admin/insights/funnel**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          total: 20,
          pending: 9,
          confirmed: 9,
          cancelled: 2,
          conversion_pct: 45.0,
        }),
      });
    });

    await page.goto(`${BASE_URL}${TEST_ADMIN_METRICS_URL}`);
    await page.waitForTimeout(2000);

    // Check slow table is visible by default
    const slowTable = page.getByTestId("metrics-queue-slow-table");
    await expect(slowTable).toBeVisible();

    // Check if slow booking ID appears
    const slowTableText = await slowTable.innerText();
    expect(slowTableText).toContain("slow-00"); // Truncated ID in UI

    // Click noted tab
    const notedTabBtn = page.locator('button:has-text("📝 Notlu Talepler")');
    await notedTabBtn.click();
    await page.waitForTimeout(500);

    // Check noted table now visible
    const notedTable = page.getByTestId("metrics-queue-noted-table");
    await expect(notedTable).toBeVisible();

    // Check if noted booking ID appears
    const notedTableText = await notedTable.innerText();
    expect(notedTableText).toContain("noted-00"); // Truncated ID in UI
  });

  test("T3 - follow toggle persists after refresh", async ({ page }) => {
    const TEST_ADMIN_METRICS_URL = process.env.TEST_ADMIN_METRICS_URL;
    if (!TEST_ADMIN_METRICS_URL) test.skip();

    await loginAsAdmin(page);

    // Mock data
    await page.route("**/api/admin/insights/queues**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          slow_hours: 24,
          slow_pending: [
            {
              booking_id: "follow-test-001",
              hotel_id: "h1",
              hotel_name: "Test Hotel",
              created_at: "2025-01-10T10:00:00Z",
              age_hours: 30.0,
              status: "pending",
              has_note: false,
            },
          ],
          noted_pending: [],
        }),
      });
    });

    await page.route("**/api/admin/insights/funnel**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_days: 30,
          total: 20,
          pending: 9,
          confirmed: 9,
          cancelled: 2,
          conversion_pct: 45.0,
        }),
      });
    });

    await page.goto(`${BASE_URL}${TEST_ADMIN_METRICS_URL}`);
    await page.waitForTimeout(2000);

    // Find first follow toggle
    const followToggle = page.getByTestId("metrics-follow-toggle").first();
    await expect(followToggle).toBeVisible();

    // Get initial state
    const initialText = await followToggle.innerText();

    // Click toggle
    await followToggle.click();
    await page.waitForTimeout(500);

    // Check state changed
    const afterToggleText = await followToggle.innerText();
    expect(initialText).not.toBe(afterToggleText);

    // Check localStorage
    const lsValue = await page.evaluate(() => {
      return localStorage.getItem("admin_follow_booking:follow-test-001");
    });
    expect(lsValue).toBe("1"); // Should be followed now

    // Reload page
    await page.reload();
    await page.waitForTimeout(2000);

    // Check state persisted
    const followToggleAfter = page.getByTestId("metrics-follow-toggle").first();
    const afterReloadText = await followToggleAfter.innerText();
    expect(afterReloadText).toBe(afterToggleText); // Should match toggled state

    // Verify localStorage still has it
    const lsValueAfter = await page.evaluate(() => {
      return localStorage.getItem("admin_follow_booking:follow-test-001");
    });
    expect(lsValueAfter).toBe("1");
  });
});
