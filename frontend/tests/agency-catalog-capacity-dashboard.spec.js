import { test, expect } from "@playwright/test";

const TEST_DATE = "2030-02-10";

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

async function ensureCapacitySetup(request, baseURL) {
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

  // 2) Ensure product exists
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
          title: "Dashboard Capacity Product",
          description: "FAZ-6 capacity dashboard test",
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

  // 3) Ensure variant exists
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
          name: "Dashboard Capacity Variant",
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

  // 4) Set capacity: max_per_day=2
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

  // 5) Create one booking on TEST_DATE with pax=2 to fully occupy the day
  const createBookingResp = await request.post(
    `${backendBase}/api/agency/catalog/bookings`,
    {
      headers: { ...authHeaders, "Content-Type": "application/json" },
      data: {
        product_id: productId,
        variant_id: variantId,
        guest: { full_name: "Dash Guest", phone: "0555", email: "dash@example.com" },
        dates: { start: TEST_DATE },
        pax: 2,
        commission_rate: 0.1,
      },
    }
  );
  expect(createBookingResp.ok()).toBeTruthy();

  return { productId, variantId };
}


test("Capacity dashboard shows full day as Dolu", async ({ page, request, baseURL }) => {
  const backendBase = baseURL?.replace(/\/$/, "") || "http://localhost:3000";

  await loginAsAgencyAdmin(page);
  const { productId, variantId } = await ensureCapacitySetup(request, backendBase);

  // Go to capacity page
  await page.goto("/app/agency/catalog/capacity", { waitUntil: "networkidle" });

  // Select product
  await page.locator("label:has-text('Ürün')").locator("..//button").click();
  await page
    .locator("[role='option']", { hasText: /Dashboard Capacity Product|Capacity Test Product|Product/ })
    .first()
    .click();

  // Select variant - pick the one we set capacity on by matching price/currency is enough
  await page.locator("label:has-text('Variant')").locator("..//button").click();
  await page.locator("[role='option']").first().click();

  // Set date range to include TEST_DATE
  await page.locator("input[type='date']").first().fill(TEST_DATE);
  await page.locator("input[type='date']").nth(1).fill(TEST_DATE);

  await page.getByRole("button", { name: "Göster" }).click();

  // Wait for grid
  const cell = page.locator(`[data-testid='capacity-cell-${TEST_DATE}']`);
  await expect(cell).toBeVisible({ timeout: 30000 });

  const used = page.locator(`[data-testid='capacity-used-${TEST_DATE}']`);
  await expect(used).toContainText("Kullanım: 2", { timeout: 30000 });

  const status = page.locator(`[data-testid='capacity-status-${TEST_DATE}']`);
  await expect(status).toHaveText("Dolu", { timeout: 30000 });
});
