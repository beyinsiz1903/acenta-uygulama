// frontend/tests/voucher-pdf-test.spec.js
import { test, expect } from "@playwright/test";

const BASE_URL = process.env.PW_BASE_URL || "http://localhost:3000";
const AGENCY_EMAIL = process.env.PW_AGENCY_EMAIL || "agency1@demo.test";
const AGENCY_PASSWORD = process.env.PW_AGENCY_PASSWORD || "agency123";

async function loginAsAgency(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: "domcontentloaded" });

  // Email
  const emailInput = page.locator('input[type="email"]').first();
  await expect(emailInput).toBeVisible({ timeout: 15000 });
  await emailInput.fill(AGENCY_EMAIL);

  // Password
  const passInput = page.locator('input[type="password"]').first();
  await expect(passInput).toBeVisible({ timeout: 15000 });
  await passInput.fill(AGENCY_PASSWORD);

  // Submit
  const submitBtn = page.get_by_role("button", name="Giriş").first();
  await expect(submitBtn).toBeVisible();
  await submitBtn.click();

  // Agency panel geldi mi?
  await page.wait_for_url(/\/app\/agency\//, { timeout: 20000 });
}

test.describe("Voucher PDF Signed URL Test", () => {
  test("C3 + Offline Payment + Voucher PDF signed URL guard scenario", async ({ page }) => {
    // 1) Login
    await loginAsAgency(page);
    console.log("✅ Login successful");

    // 2) Navigate to tour bookings
    await page.goto(`${BASE_URL}/app/agency/tour-bookings`, { waitUntil: "domcontentloaded" });
    await page.wait_for_timeout(2000);
    
    // Check if page loaded
    await expect(page.get_by_text(/tur rezervasyon talepleri/i)).toBeVisible({ timeout: 15000 });
    console.log("✅ Tour bookings page loaded");

    // 3) Switch to "Onaylandı" (Approved) status to find bookings with vouchers
    const approvedBtn = page.get_by_role("button", name="Onaylandı").first();
    await approvedBtn.click();
    await page.wait_for_timeout(2000);
    console.log("✅ Switched to 'Onaylandı' status filter");

    // 4) Navigate directly to a booking with voucher (we know ID from API call)
    const bookingId = "69518dbec791416a44623fe0"; // This booking has voucher metadata
    await page.goto(`${BASE_URL}/app/agency/tour-bookings/${bookingId}`, { waitUntil: "domcontentloaded" });
    await page.wait_for_timeout(3000);
    console.log("✅ Navigated to booking detail page");

    // 5) Verify we're on the detail page
    await expect(page.locator("body")).toContainText(/tur rezervasyon talebi/i);
    console.log("✅ Booking detail page loaded");

    // 6) Check for tel link (optional - might not exist)
    const telLinks = page.locator('a[href^="tel:"]');
    const telCount = await telLinks.count();
    if (telCount > 0) {
      const href = await telLinks.first().get_attribute("href");
      expect(href).toBeTruthy();
      expect(href.startsWith("tel:")).toBeTruthy();
      console.log(`✅ Tel link found: ${href}`);
    } else {
      console.log("ℹ️ No tel links found (guest may not have phone number)");
    }

    // 7) Check for offline payment card (should exist)
    const offlineCard = page.locator('[data-testid="offline-payment-card"]');
    await expect(offlineCard).toBeVisible({ timeout: 10000 });
    console.log("✅ Offline payment card found");

    // 8) Test copy functionality
    const copyIban = page.locator('[data-testid="btn-copy-iban"]').first();
    const copyRef = page.locator('[data-testid="btn-copy-reference"]').first();
    const copyNote = page.locator('[data-testid="btn-copy-payment-note"]').first();

    if (await copyIban.count() > 0) {
      await copyIban.click();
      await expect(page.locator("body")).toContainText(/IBAN.*panoya kopyalandı/i, { timeout: 8000 });
      console.log("✅ IBAN copy functionality working");
    }

    if (await copyRef.count() > 0) {
      await copyRef.click();
      await expect(page.locator("body")).toContainText(/Referans kodu.*panoya kopyalandı/i, { timeout: 8000 });
      console.log("✅ Reference code copy functionality working");
    }

    if (await copyNote.count() > 0) {
      await copyNote.click();
      await expect(page.locator("body")).toContainText(/Ödeme açıklaması.*panoya kopyalandı/i, { timeout: 8000 });
      console.log("✅ Payment note copy functionality working");
    }

    // 9) MAIN TEST: Voucher PDF signed URL functionality
    const voucherBtn = page.locator('[data-testid="btn-open-tour-voucher-pdf"]');
    await expect(voucherBtn).toBeVisible({ timeout: 10000 });
    console.log("✅ Voucher PDF button found");

    // 10) Test the voucher signed URL API call
    const [signedResponse] = await Promise.all([
      page.wait_for_response((res) => {
        const url = res.url();
        return (
          url.includes("/api/agency/tour-bookings/") &&
          url.includes("/voucher-signed-url") &&
          res.request().method() === "POST"
        );
      }),
      voucherBtn.click(),
    ]);

    expect(signedResponse.ok()).toBeTruthy();
    console.log(`✅ POST /voucher-signed-url API call successful: ${signedResponse.status()}`);

    // 11) Verify response structure
    const responseBody = await signedResponse.json();
    const signedUrl = responseBody.url;
    const expiresAt = responseBody.expires_at;

    expect(signedUrl).toBeTruthy();
    expect(signedUrl).toMatch(/^\/api\/public\/vouchers\/.*\.pdf\?t=/);
    console.log(`✅ Response JSON contains url: ${signedUrl}`);

    expect(expiresAt).toBeTruthy();
    expect(expiresAt).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/); // ISO string format
    console.log(`✅ Response JSON contains expires_at: ${expiresAt}`);

    // 12) Test the PDF endpoint directly
    const backendBase = process.env.REACT_APP_BACKEND_URL || process.env.PW_BACKEND_URL || BASE_URL;
    const fullUrl = signedUrl.startsWith("http") ? signedUrl : `${backendBase}${signedUrl}`;
    
    console.log(`Testing PDF endpoint: ${fullUrl}`);
    
    const pdfResponse = await page.request.get(fullUrl);
    expect(pdfResponse.status()).toBe(200);
    console.log(`✅ PDF endpoint response status: ${pdfResponse.status()}`);

    const headers = pdfResponse.headers();
    const contentType = headers["content-type"] || headers["Content-Type"] || "";
    expect(contentType.toLowerCase()).toContain("application/pdf");
    console.log(`✅ Content-Type header verification successful: ${contentType}`);

    console.log("🎉 All voucher PDF signed URL guard tests passed!");
  });
});