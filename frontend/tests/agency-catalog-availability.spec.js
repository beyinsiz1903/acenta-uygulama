import { test, expect } from "@playwright/test";

async function loginAsAgencyAdmin(page) {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.fill('[data-testid="login-email"]', "agency1@demo.test");
  await page.fill('[data-testid="login-password"]', "agency123");
  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    page.click('[data-testid="login-submit"]'),
  ]);
  await expect(page).toHaveURL(/\/app\//, { timeout: 30000 });
}

async function ensureProductAndVariant(request, baseURL) {
  const backendBase = baseURL.replace(/\/$/, "");

  // 1) Login to get token
  const loginResp = await request.post(`${backendBase}/api/auth/login`, {
    data: { email: "agency1@demo.test", password: "agency123" },
  });
  expect(loginResp.ok()).toBeTruthy();
  const loginJson = await loginResp.json();
  const token = loginJson.access_token || loginJson.token;
  expect(token).toBeTruthy();

  const authHeaders = { Authorization: `Bearer ${token}` };

  // 2) Ensure at least one product exists (reuse earlier created product if any)
  const prodList = await request.get(
    `${backendBase}/api/agency/catalog/products?limit=1`,
    { headers: authHeaders }
  );
  expect(prodList.ok()).toBeTruthy();
  const prodJson = await prodList.json();
  let productId = prodJson.items?.[0]?.id;

  if (!productId) {
    const createProdResp = await request.post(
      `${backendBase}/api/agency/catalog/products`,
      {
        headers: { ...authHeaders, "Content-Type": "application/json" },
        data: {
          type: "tour",
          title: "Capacity Test Product",
          description: "FAZ-5 capacity test",
          location: { city: "Sapanca", country: "TR" },
          base_currency: "TRY",
          images: [],
        },
      }
    );
    expect(createProdResp.ok()).toBeTruthy();
    const cp = await createProdResp.json();
    productId = cp.id;
  }

  // 3) Ensure at least one variant with capacity
  const varList = await request.get(
    `${backendBase}/api/agency/catalog/products/${productId}/variants?limit=1`,
    { headers: authHeaders }
  );
  expect(varList.ok()).toBeTruthy();
  const varJson = await varList.json();
  let variantId = varJson.items?.[0]?.id;

  if (!variantId) {
    const createVarResp = await request.post(
      `${backendBase}/api/agency/catalog/variants`,
      {
        headers: { ...authHeaders, "Content-Type": "application/json" },
        data: {
          product_id: productId,
          name: "Capacity Variant",
          price: 1000,
          currency: "TRY",
          rules: { min_pax: 1, max_pax: 5 },
          active: true,
        },
      }
    );
    expect(createVarResp.ok()).toBeTruthy();
    const cv = await createVarResp.json();
    variantId = cv.id;
  }

  // 4) Set capacity: mode=pax, max_per_day=2, overbook=false
  const setCapResp = await request.put(
    `${backendBase}/api/agency/catalog/variants/${variantId}`,
    {
      headers: { ...authHeaders, "Content-Type": "application/json" },
      data: {
        capacity: { mode: "pax", max_per_day: 2, overbook: false },
      },
    }
  );
  expect(setCapResp.ok()).toBeTruthy();

  return { productId, variantId, token };
}


const TEST_DATE = "2030-01-10";

async function createBookingViaUI(page) {
  await page.goto("/app/agency/catalog/bookings", { waitUntil: "networkidle" });

  const createBtn = page.locator('[data-testid="btn-catalog-create-booking"]');
  await expect(createBtn).toBeVisible({ timeout: 30000 });
  await createBtn.click();

  // Wait for modal
  await expect(page.locator('[data-testid="catalog-booking-create-modal"]')).toBeVisible({ timeout: 30000 });

  // Pick first product
  await page.locator('[data-testid="catalog-booking-select-product"]').click();
  await page.locator('[data-testid="catalog-booking-product-item"]').first().click();

  // Variant (optional) - select first if exists
  const hasVariantTrigger = await page.locator('[data-testid="catalog-booking-select-variant"]').count();
  if (hasVariantTrigger > 0) {
    const trigger = page.locator('[data-testid="catalog-booking-select-variant"]');
    await trigger.click();
    const options = page.locator("[role='option']");
    if (await options.count()) {
      await options.first().click();
    }
  }

  await page.locator('[data-testid="catalog-booking-guest-fullname"]').fill("Capacity Guest");
  await page.locator('[data-testid="catalog-booking-start-date"]').fill(TEST_DATE);
  await page.locator('[data-testid="catalog-booking-pax"]').fill("2");

  // Wait for availability to say can_book true
  const availStatus = page.locator('[data-testid="availability-status"]');
  await expect(availStatus).toContainText("Uygun", { timeout: 30000 });

  await Promise.all([
    page.waitForURL(/\/app\/agency\/catalog\/bookings\//, { timeout: 30000 }),
    page.locator('[data-testid="btn-catalog-submit-booking"]').click(),
  ]);

  await expect(page).toHaveURL(/\/app\/agency\/catalog\/bookings\//, { timeout: 30000 });
}


test("Catalog availability: capacity blocks second booking on same day", async ({ page, request, baseURL }) => {
  const backendBase = baseURL?.replace(/\/$/, "") || "http://localhost:3000";

  await loginAsAgencyAdmin(page);
  await ensureProductAndVariant(request, backendBase);

  // 1) First booking: pax=2 on 2026-01-10 (should pass)
  await createBookingViaUI(page);

  // 2) Second booking attempt on same day with pax=1 should be blocked
  await page.goto("/app/agency/catalog/bookings", { waitUntil: "networkidle" });
  const createBtn2 = page.locator('[data-testid="btn-catalog-create-booking"]');
  await expect(createBtn2).toBeVisible({ timeout: 30000 });
  await createBtn2.click();

  await expect(page.locator('[data-testid="catalog-booking-create-modal"]')).toBeVisible({ timeout: 30000 });

  await page.locator('[data-testid="catalog-booking-select-product"]').click();
  await page.locator('[data-testid="catalog-booking-product-item"]').first().click();

  const hasVariantTrigger2 = await page.locator('[data-testid="catalog-booking-select-variant"]').count();
  if (hasVariantTrigger2 > 0) {
    const trigger2 = page.locator('[data-testid="catalog-booking-select-variant"]');
    await trigger2.click();
    const options2 = page.locator("[role='option']");
    if (await options2.count()) {
      await options2.first().click();
    }
  }

  await page.locator('[data-testid="catalog-booking-guest-fullname"]').fill("Capacity Guest 2");
  await page.locator('[data-testid="catalog-booking-start-date"]').fill(TEST_DATE);
  await page.locator('[data-testid="catalog-booking-pax"]').fill("1");

  const availStatus2 = page.locator('[data-testid="availability-status"]');
  await expect(availStatus2).toBeVisible({ timeout: 30000 });
  await expect(availStatus2).toContainText("Kapasite dolu", { timeout: 30000 });

  const submitBtn = page.locator('[data-testid="btn-catalog-submit-booking"]');
  await expect(submitBtn).toBeEnabled({ timeout: 30000 });

  // Try to submit and expect a 409 CAPACITY_NOT_AVAILABLE via network assertion
  const [response] = await Promise.all([
    page.waitForResponse((resp) => {
      return resp.url().includes("/api/agency/catalog/bookings") && resp.request().method() === "POST";
    }),
    submitBtn.click(),
  ]);

  expect(response.status()).toBe(409);
  const json = await response.json();
  expect(json.detail?.code).toBe("CAPACITY_NOT_AVAILABLE");
});
