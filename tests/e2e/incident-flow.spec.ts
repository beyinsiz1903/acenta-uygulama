import { test, expect } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
const BACKEND_URL = process.env.E2E_BACKEND_URL || "http://localhost:8001";
const ADMIN_EMAIL = "admin@acenta.test";
const ADMIN_PASSWORD = "admin123";

async function loginAsSuperAdmin(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState("networkidle");
  await page.getByTestId("login-email").fill(ADMIN_EMAIL);
  await page.getByTestId("login-password").fill(ADMIN_PASSWORD);
  await Promise.all([
    page.waitForURL(/\/app/, { timeout: 15000 }),
    page.getByTestId("login-submit").click(),
  ]);
}

async function getAuthToken(request) {
  const resp = await request.post(`${BACKEND_URL}/api/auth/login`, {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  });
  const body = await resp.json();
  return body.access_token;
}

test.describe("Incident Lifecycle Flow", () => {
  test("create incident, verify in list, resolve, verify resolution", async ({ page, request }) => {
    const authToken = await getAuthToken(request);
    await loginAsSuperAdmin(page);

    // Navigate to incidents page
    await page.goto(`${BASE_URL}/app/admin/system-incidents`);
    await page.waitForLoadState("networkidle");

    const pageEl = page.getByTestId("system-incidents-page");
    await expect(pageEl).toBeVisible({ timeout: 10000 });
    console.log("✅ System Incidents page loaded");

    // 1. Create a new incident via UI
    const createBtn = page.getByTestId("create-incident-btn");
    await expect(createBtn).toBeVisible();
    await createBtn.click();

    // Fill the form
    const form = page.getByTestId("create-incident-form");
    await expect(form).toBeVisible();

    const titleInput = page.getByTestId("incident-title-input");
    await titleInput.fill("E2E Test Incident - DB Latency Spike");

    const rootCauseInput = page.getByTestId("incident-root-cause-input");
    await rootCauseInput.fill("MongoDB connection pool exhaustion during peak traffic");

    // Submit
    const submitBtn = page.getByTestId("submit-incident-btn");
    await submitBtn.click();
    console.log("✅ Incident creation submitted");

    await page.waitForTimeout(2000);

    // 2. Verify incident appears in the list
    const list = page.getByTestId("incidents-list");
    await expect(list).toBeVisible({ timeout: 10000 });

    const listText = await list.textContent();
    expect(listText).toContain("E2E Test Incident");
    expect(listText).toContain("DB Latency Spike");
    console.log("✅ Incident visible in list");

    // 3. Resolve the incident via UI
    const resolveBtn = page.getByTestId("resolve-btn").first();
    await expect(resolveBtn).toBeVisible();
    await resolveBtn.click();

    // Fill resolve notes
    const resolveForm = page.getByTestId("resolve-form");
    await expect(resolveForm).toBeVisible();

    const resolveNotes = page.getByTestId("resolve-notes-input");
    await resolveNotes.fill("Increased connection pool size to 200. Latency normalized.");

    const submitResolve = page.getByTestId("submit-resolve-btn");
    await submitResolve.click();
    console.log("✅ Incident resolve submitted");

    await page.waitForTimeout(2000);

    // 4. Verify the incident is now resolved (shows Çözüldü badge)
    const updatedList = await page.getByTestId("incidents-list").textContent();
    expect(updatedList).toContain("Çözüldü");
    expect(updatedList).toContain("Increased connection pool size");
    console.log("✅ Incident resolved and resolution notes visible");

    // 5. Also verify via API that the incident has end_time
    const apiResp = await request.get(`${BACKEND_URL}/api/admin/system/incidents`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const apiBody = await apiResp.json();
    const testIncident = apiBody.items.find(
      (i: any) => i.title?.includes("E2E Test Incident")
    );
    expect(testIncident).toBeTruthy();
    expect(testIncident.end_time).toBeTruthy();
    expect(testIncident.resolution_notes).toContain("Increased connection pool");
    console.log("✅ API confirms incident resolved with end_time and resolution_notes");
  });
});
