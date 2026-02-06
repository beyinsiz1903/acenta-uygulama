import { test, expect } from "@playwright/test";

const BASE_URL = "https://enterprise-ops-8.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test.describe("Activation Checklist", () => {
  let token: string;

  test.beforeAll(async ({ request }) => {
    const signup = await request.post(`${BASE_URL}/api/onboarding/signup`, {
      data: {
        company_name: `ChecklistCo_${UID}`,
        admin_name: "Checklist Admin",
        email: `checklist_${UID}@test.com`,
        password: "test123456",
        plan: "starter",
        billing_cycle: "monthly",
      },
    });
    expect(signup.ok()).toBeTruthy();
    const d = await signup.json();
    token = d.access_token;
  });

  test("checklist auto-created with 7 items", async ({ request }) => {
    const res = await request.get(`${BASE_URL}/api/activation/checklist`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.items.length).toBe(7);
    expect(body.completed_count).toBe(0);
    expect(body.all_completed).toBe(false);
  });

  test("complete item updates state and persists", async ({ request }) => {
    // Complete one item
    const put = await request.put(`${BASE_URL}/api/activation/checklist/create_product/complete`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(put.ok()).toBeTruthy();
    const putBody = await put.json();
    expect(putBody.ok).toBe(true);
    expect(putBody.already_completed).toBe(false);

    // Verify persisted
    const get = await request.get(`${BASE_URL}/api/activation/checklist`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(get.ok()).toBeTruthy();
    const body = await get.json();
    expect(body.completed_count).toBe(1);

    const item = body.items.find((i: any) => i.key === "create_product");
    expect(item.completed_at).toBeTruthy();
  });

  test("completing same item again returns already_completed", async ({ request }) => {
    const put = await request.put(`${BASE_URL}/api/activation/checklist/create_product/complete`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(put.ok()).toBeTruthy();
    const body = await put.json();
    expect(body.already_completed).toBe(true);
  });
});
