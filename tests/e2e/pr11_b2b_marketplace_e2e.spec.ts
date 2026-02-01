import { test, expect, request as pwRequest } from '@playwright/test';

async function loginAsSuperAdmin(page) {
  await page.goto('/login');

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

function requireBackendBaseURL(): string {
  const explicit = process.env.E2E_BACKEND_URL || process.env.REACT_APP_BACKEND_URL;
  if (!explicit) {
    throw new Error(
      'E2E_BACKEND_URL is required for seeding (must point to backend origin, e.g. http://localhost:8001).',
    );
  }
  return explicit.replace(/\/$/, '');
}

// PR-11 gate: exit_b2b_marketplace_e2e_v1
// Covers:
// - Tenant key deterministik olarak set
// - "Vitrine gönder" CTA: bridge endpoint 200 + redirect_url
// - "B2B Taslak Oluştur" CTA: /api/b2b/bookings 201 + booking_id
// - Negatif: tenant yokken uygun hata mesajı

async function ensureMarketplaceSeed(baseURL: string) {
  const backendOrigin = requireBackendBaseURL();
  const apiBase = backendOrigin.endsWith('/api') ? backendOrigin : `${backendOrigin}/api`;
  console.log(`[e2e-seed] apiBase=${apiBase}`);

  const runId = process.env.CI
    ? `ci-${process.env.GITHUB_RUN_ID || 'unknown'}`
    : `local-${Date.now()}`;
  console.log(`[e2e-seed] runId=${runId}`);

  const apiRequest = await pwRequest.newContext({ baseURL: apiBase });

  try {
    // 1) API login as super admin (same creds as UI)
    const loginRes = await apiRequest.post('/api/auth/login', {
      data: {
        email: 'muratsutay@hotmail.com',
        password: 'murat1903',
      },
    });
    if (!loginRes.ok()) {
      throw new Error(`Login failed: ${loginRes.status()} ${await loginRes.text()}`);
    }
    const loginBody = await loginRes.json();
    const token = loginBody.access_token || loginBody.token || loginBody.jwt;
    if (!token) {
      throw new Error(
        `[e2e-seed] No token in /auth/login response keys=${Object.keys(loginBody).join(',')}`,
      );
    }

    const authHeaders = {
      Authorization: `Bearer ${token}`,
    };
    console.log('[e2e-seed] login ok');

    // 2) Create & publish listing under a known seller tenant
    const sellerTenantKey = 'seller-tenant-br';
    const buyerTenantKey = 'buyer-b2b';

    const createRes = await apiRequest.post('/marketplace/listings', {
      headers: {
        ...authHeaders,
        'X-Tenant-Key': sellerTenantKey,
      },
      data: {
        title: 'E2E Listing - PR13',
        description: 'E2E test listing for PR-13',
        category: 'hotel',
        currency: 'TRY',
        base_price: '100.00',
        tags: ['pr13', 'e2e'],
      },
    });

    if (!createRes.ok()) {
      throw new Error(`Create listing failed: ${createRes.status()} ${await createRes.text()}`);
    }
    const created = await createRes.json();
    const listingId = created.id;
    console.log('[e2e-seed] listing created:', listingId);

    // 2.b) Publish listing
    const publishRes = await apiRequest.post(`/marketplace/listings/${listingId}/publish`, {
      headers: {
        ...authHeaders,
        'X-Tenant-Key': sellerTenantKey,
      },
    });
    if (!publishRes.ok()) {
      throw new Error(`Publish listing failed: ${publishRes.status()} ${await publishRes.text()}`);
    }
    console.log('[e2e-seed] listing published');

    // 3) Grant access seller->buyer using tenant keys (idempotent via upsert in backend)
    const grantRes = await apiRequest.post('/marketplace/access/grant', {
      headers: authHeaders,
      data: {
        seller_tenant_key: sellerTenantKey,
        buyer_tenant_key: buyerTenantKey,
      },
    });
    if (!grantRes.ok()) {
      throw new Error(`Grant access failed: ${grantRes.status()} ${await grantRes.text()}`);
    }
    console.log('[e2e-seed] access granted');

    // 4) Sanity check: buyer catalog sees at least one item
    const catalogRes = await apiRequest.get('/marketplace/catalog', {
      headers: {
        ...authHeaders,
        'X-Tenant-Key': buyerTenantKey,
      },
    });
    if (!catalogRes.ok()) {
      throw new Error(`Catalog failed: ${catalogRes.status()} ${await catalogRes.text()}`);
    }
    const catalogBody = await catalogRes.json();
    const items = catalogBody.items || [];
    if (!items.length) {
      throw new Error('[e2e-seed] catalog returned 0 items for buyer-b2b');
    }
    console.log('[e2e-seed] catalog ok items=', items.length);
  } finally {
    await apiRequest.dispose();
  }
}

// PR-11 gate: exit_b2b_marketplace_e2e_v1

test.describe('PR-11 B2B Marketplace E2E (@exit_b2b_marketplace_e2e_v1)', () => {
  test('exit_b2b_marketplace_e2e_v1 - happy paths and negative tenant case', async ({ page, baseURL }) => {
    if (!baseURL) {
      throw new Error('baseURL is not defined in Playwright config');
    }

    // Seed data via API (idempotent)
    await ensureMarketplaceSeed(baseURL);

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

    // Page heading inside main content
    await expect(page.getByRole('main').getByText('B2B Marketplace')).toBeVisible();

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

    // Page heading inside main content
    await expect(page.getByRole('main').getByText('B2B Marketplace')).toBeVisible();

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
