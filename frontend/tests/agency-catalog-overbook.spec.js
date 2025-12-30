import { test, expect } from "@playwright/test";

const TEST_DATE = "2030-05-10";

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

async function ensureVariantOverbookEnabled(request, baseURL) {
  const backendBase = baseURL.replace(/\/$/, "");

  const loginResp = await request.post(`${backendBase}/api/auth/login`, {
    data: { email: "agency1@demo.test", password: "agency123" },
  });
  expect(loginResp.ok()).toBeTruthy();
  const loginJson = await loginResp.json();
  const token = loginJson.access_token || loginJson.token;
  const authHeaders = { Authorization: `Bearer ${token}` };

  // Product
  const prodList = await request.get(
    `${backendBase}/api/agency/catalog/products?limit=1`,
    { headers: authHeaders }
  );
  expect(prodList.ok()).toBeTruthy();
  const prodJson = await prodList.json();
  let productId = prodJson.items?.[0]?.id;
  if (!productId) {
    const cpResp = await request.post(`${backendBase}/api/agency/catalog/products`, {
      headers: { ...authHeaders, "Content-Type": "application/json" },
      data: {
        type: "tour",
        title: "Overbook Product",
        description: "FAZ-7 overbook test",
        location: { city: "Sapanca", country: "TR" },
        base_currency: "TRY",
        images: [],
      },
    });
    expect(cpResp.ok()).toBeTruthy();
    const cp = await cpResp.json();
    productId = cp.id;
  }

  // Variant
  const varList = await request.get(
    `${backendBase}/api/agency/catalog/products/${productId}/variants?limit=1`,
    { headers: authHeaders }
  );
  expect(varList.ok()).toBeTruthy();
  const varJson = await varList.json();
  let variantId = varJson.items?.[0]?.id;
  if (!variantId) {
    const cvResp = await request.post(`${backendBase}/api/agency/catalog/variants`, {
      headers: { ...authHeaders, "Content-Type": "application/json" },
      data: {
        product_id: productId,
        name: "Overbook Variant",
        price: 1000,
        currency: "TRY",
        rules: { min_pax: 1, max_pax: 5 },
        active: true,
      },
    });
    expect(cvResp.ok()).toBeTruthy();
    const cv = await cvResp.json();
    variantId = cv.id;
  }

  // Enable overbook and set capacity=2
  const setCapResp = await request.put(
    `${backendBase}/api/agency/catalog/variants/${variantId}`,
    {
      headers: { ...authHeaders, "Content-Type": "application/json" },
      data: {
        capacity: { mode: "pax", max_per_day: 2, overbook: true },
      },
    }
  );
  expect(setCapResp.ok()).toBeTruthy();

  return { productId, variantId };
}

async function createBooking(page, { date, pax }) {
  await page.goto("/app/agency/catalog/bookings", { waitUntil: "networkidle" });

  const createBtn = page.locator('[data-testid="btn-catalog-create-booking"]');
  await expect(createBtn).toBeVisible({ timeout: 30000 });
  await createBtn.click();

  await expect(page.locator('[data-testid="catalog-booking-create-modal"]')).toBeVisible({ timeout: 30000 });

  await page.locator('[data-testid="catalog-booking-select-product"]').click();
  await page.locator('[data-testid="catalog-booking-product-item"]').first().click();

  const hasVariantTrigger = await page.locator('[data-testid="catalog-booking-select-variant"]').count();
  if (hasVariantTrigger > 0) {
    const trigger = page.locator('[data-testid="catalog-booking-select-variant"]');
    await trigger.click();
    const options = page.locator("[role='option']");
    if (await options.count()) {
      await options.first().click();
    }
  }

  await page.locator('[data-testid="catalog-booking-guest-fullname"]').fill("Overbook Guest");
  await page.locator('[data-testid="catalog-booking-start-date"]').fill(date);
  await page.locator('[data-testid="catalog-booking-pax"]').fill(String(pax));

  // Wait for availability status (Uygun veya Overbook)
  const availStatus = page.locator('[data-testid="availability-status"]');
  await expect(availStatus).toBeVisible({ timeout: 30000 });

  await Promise.all([
    page.waitForURL(/\/app\/agency\/catalog\/bookings\//, { timeout: 30000 }),
    page.locator('[data-testid="btn-catalog-submit-booking"]').click(),
  ]);

  await expect(page).toHaveURL(/\/app\/agency\/catalog\/bookings\//, { timeout: 30000 });
}


test("Overbook flow: second booking overbooks capacity and is visible in UI + dashboard", async ({ page, request, baseURL }) => {
  const backendBase = baseURL?.replace(/\/$/, "") || "http://localhost:3000";

  await loginAsAgencyAdmin(page);
  await ensureVariantOverbookEnabled(request, backendBase);

  // 1) First booking fills capacity (pax=2)
  await createBooking(page, { date: TEST_DATE, pax: 2 });

  // 2) Second booking on same day (pax=1) should overbook (still 200)
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

  await page.locator('[data-testid="catalog-booking-guest-fullname"]').fill("Overbook Guest 2");
  await page.locator('[data-testid="catalog-booking-start-date"]').fill(TEST_DATE);
  await page.locator('[data-testid="catalog-booking-pax"]').fill("1");

  const availStatus2 = page.locator('[data-testid="availability-status"]');
  await expect(availStatus2).toBeVisible({ timeout: 30000 });

  const [response] = await Promise.all([
    page.waitForResponse((resp) => resp.url().includes("/api/agency/catalog/bookings") && resp.request().method() === "POST"),
    page.locator('[data-testid="btn-catalog-submit-booking"]').click(),
  ]);

  expect(response.status()).toBe(200);
  const json = await response.json();
  expect(json.allocation?.overbook).toBeTruthy();

  // Booking detail should show overbook badge
  await expect(page.locator('[data-testid="booking-overbook-badge"]')).toBeVisible({ timeout: 30000 });

  // Capacity dashboard should show day as Dolu and overbooked
  await page.goto("/app/agency/catalog/capacity", { waitUntil: "networkidle" });
  await page.locator("label:has-text('Ürün')").locator("..//button").click();
  await page.locator("[role='option']").first().click();
  await page.locator("label:has-text('Variant')").locator("..//button").click();
  await page.locator("[role='option']").first().click();

  await page.locator("input[type='date']").first().fill(TEST_DATE);
  await page.locator("input[type='date']").nth(1).fill(TEST_DATE);

  await page.getByRole("button", { name: "Göster" }).click();

  const cell = page.locator(`[data-testid='capacity-cell-${TEST_DATE}']`);
  await expect(cell).toBeVisible({ timeout: 30000 });

  const status = page.locator(`[data-testid='capacity-status-${TEST_DATE}']`);
  await expect(status).toHaveText("Dolu", { timeout: 30000 });
});
