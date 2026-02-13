import { test, expect } from "@playwright/test";

const BASE = "https://nostalgic-ganguly-1.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test("activation-checklist: create, complete, persist", async ({ request }) => {
  // Signup
  const su = await request.post(`${BASE}/api/onboarding/signup`, {
    data: {
      company_name: `CL_${UID}`,
      admin_name: "Admin",
      email: `cl_${UID}@test.com`,
      password: "test123456",
      plan: "starter",
      billing_cycle: "monthly",
    },
  });
  expect(su.ok()).toBeTruthy();
  const { access_token: token } = await su.json();
  const h = { Authorization: `Bearer ${token}` };

  // 1) GET checklist - auto-created with 7 items
  const g1 = await request.get(`${BASE}/api/activation/checklist`, { headers: h });
  expect(g1.ok()).toBeTruthy();
  const c1 = await g1.json();
  expect(c1.items.length).toBe(7);
  expect(c1.completed_count).toBe(0);
  expect(c1.all_completed).toBe(false);

  // 2) Complete one item
  const p1 = await request.put(`${BASE}/api/activation/checklist/create_product/complete`, { headers: h });
  expect(p1.ok()).toBeTruthy();
  const pr = await p1.json();
  expect(pr.ok).toBe(true);
  expect(pr.already_completed).toBe(false);

  // 3) Verify persisted
  const g2 = await request.get(`${BASE}/api/activation/checklist`, { headers: h });
  expect(g2.ok()).toBeTruthy();
  const c2 = await g2.json();
  expect(c2.completed_count).toBe(1);
  const item = c2.items.find((i: any) => i.key === "create_product");
  expect(item.completed_at).toBeTruthy();

  // 4) Re-complete returns already_completed
  const p2 = await request.put(`${BASE}/api/activation/checklist/create_product/complete`, { headers: h });
  expect(p2.ok()).toBeTruthy();
  expect((await p2.json()).already_completed).toBe(true);
});
