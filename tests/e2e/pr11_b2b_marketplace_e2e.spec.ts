import { test, expect } from '@playwright/test';

// Helper: perform login using existing /login page (admin@acenta.test / admin123)
async function loginAsSuperAdmin(page) {
  await page.goto('/login');

  // Fill demo credentials if not already filled
  const emailInput = page.getByTestId('login-email');
  const passwordInput = page.getByTestId('login-password');
  const submitButton = page.getByTestId('login-submit');

  await emailInput.fill('muratsutay@hotmail.com');
  await passwordInput.fill('murat1903');

  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle' }),
    submitButton.click(),
  ]);
}

// PR-11 gate: exit_b2b_marketplace_e2e_v1
// Covers:
// - Tenant key deterministik olarak set
// - "Vitrine gönder" CTA: bridge endpoint 200 + redirect_url
// - "B2B Taslak Oluştur" CTA: /api/b2b/bookings 201 + booking_id
// - Negatif: tenant yokken uygun hata mesajı

test.describe('PR-11 B2B Marketplace E2E (@exit_b2b_marketplace_e2e_v1)', () => {
  test('exit_b2b_marketplace_e2e_v1 - happy paths and negative tenant case', async ({ page }) => {
    // 1) Login as super admin via existing login flow
    await loginAsSuperAdmin(page);

    // 1.a) Deterministic tenant key in localStorage BEFORE navigating
    await page.addInitScript(() => {
      try {
        window.localStorage.setItem('marketplace:tenantKey', 'buyer-b2b');
      } catch {
        // ignore
      }
    });

    // 2) Navigate to /app/b2b/marketplace inside auth-protected shell
    await page.goto('/app/b2b/marketplace');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText('B2B Marketplace')).toBeVisible();

    // Ensure at least one listing card exists
    const cards = page.locator('div.grid div[data-testid="marketplace-card"], div.grid .flex.flex-col.justify-between');
    const cardCount = await cards.count();
    expect(cardCount).toBeGreaterThan(0);

    const firstCard = cards.first();

    // 3) "Vitrine gönder" CTA - focus on network assertion
    const vitrineButton = firstCard.getByRole('button', { name: 'Vitrine gönder' });
    await expect(vitrineButton).toBeVisible();

    const vitrineRequestPromise = page.waitForRequest((req) => {
      return (
        req.method() === 'POST' &&
        req.url().includes('/api/marketplace/catalog/') &&
        req.url().includes('/create-storefront-session')
      );
    });

    const vitrineResponsePromise = page.waitForResponse((res) => {
      return (
        res.request().method() === 'POST' &&
        res.url().includes('/api/marketplace/catalog/') &&
        res.url().includes('/create-storefront-session')
      );
    });

    await vitrineButton.click();

    const vitrineReq = await vitrineRequestPromise;
    const vitrineRes = await vitrineResponsePromise;

    expect(vitrineReq).toBeTruthy();
    expect(vitrineRes.status()).toBe(200);

    const vitrineBody = await vitrineRes.json();
    expect(typeof vitrineBody.redirect_url).toBe('string');
    expect(vitrineBody.redirect_url.length).toBeGreaterThan(0);

    // 4) "B2B Taslak Oluştur" CTA - network + response + alert
    const taslakButton = firstCard.getByRole('button', { name: 'B2B Taslak Oluştur' });
    await expect(taslakButton).toBeVisible();

    const bookingRequestPromise = page.waitForRequest((req) => {
      return req.method() === 'POST' && req.url().includes('/api/b2b/bookings');
    });

    const bookingResponsePromise = page.waitForResponse((res) => {
      return res.request().method() === 'POST' && res.url().includes('/api/b2b/bookings');
    });

    const dialogPromise = page.waitForEvent('dialog');

    await taslakButton.click();

    const bookingReq = await bookingRequestPromise;
    const bookingRes = await bookingResponsePromise;
    const dialog = await dialogPromise;

    expect(bookingReq).toBeTruthy();
    expect(bookingRes.status()).toBe(201);

    const bookingBody = await bookingRes.json();
    expect(typeof bookingBody.booking_id).toBe('string');
    expect(bookingBody.booking_id.length).toBeGreaterThan(0);

    // Basic ObjectId-like / UUID-like shape check (minimal, just non-empty)
    const dialogMessage = dialog.message();
    expect(dialogMessage).toContain('Taslak oluşturuldu:');
    // Close alert
    await dialog.dismiss();

    // 5) Negative case: tenant key yokken B2B Taslak Oluştur
    // Reload without tenant key in localStorage
    await page.addInitScript(() => {
      try {
        window.localStorage.removeItem('marketplace:tenantKey');
      } catch {
        // ignore
      }
    });

    await page.goto('/app/b2b/marketplace');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText('B2B Marketplace')).toBeVisible();

    const cards2 = page.locator('div.grid div[data-testid="marketplace-card"], div.grid .flex.flex-col.justify-between');
    const firstCard2 = cards2.first();
    const taslakButton2 = firstCard2.getByRole('button', { name: 'B2B Taslak Oluştur' });
    await expect(taslakButton2).toBeVisible();

    await taslakButton2.click();

    // Beklenen hata mesajı: "Tenant seçmelisiniz."
    const errorLocator = page.getByText('Tenant seçmelisiniz.');
    await expect(errorLocator).toBeVisible();
  });
});
