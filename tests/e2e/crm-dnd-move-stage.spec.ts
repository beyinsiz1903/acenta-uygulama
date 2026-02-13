import { test, expect } from "@playwright/test";

const BASE = "https://availability-perms.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test("dnd-stage-move: move deal via API + verify persistence", async ({ request }) => {
  // Signup
  const su = await request.post(`${BASE}/api/onboarding/signup`, {
    data: { company_name: `DnD_${UID}`, admin_name: "Admin", email: `dnd_${UID}@test.com`, password: "test123456", plan: "starter", billing_cycle: "monthly" },
  });
  expect(su.ok()).toBeTruthy();
  const { access_token: token } = await su.json();
  const h = { Authorization: `Bearer ${token}` };

  // Create deal in lead
  const cd = await request.post(`${BASE}/api/crm/deals`, {
    headers: h,
    data: { title: `DnD Deal ${UID}`, amount: 20000, currency: "TRY", stage: "lead" },
  });
  expect(cd.ok()).toBeTruthy();
  const deal = await cd.json();
  expect(deal.stage).toBe("lead");

  // Move via move-stage API (simulating DnD)
  const m1 = await request.post(`${BASE}/api/crm/deals/${deal.id}/move-stage`, {
    headers: h, data: { stage: "contacted" },
  });
  expect(m1.ok()).toBeTruthy();
  expect((await m1.json()).stage).toBe("contacted");

  // Verify persistence - fetch deal again
  const g1 = await request.get(`${BASE}/api/crm/deals/${deal.id}`, { headers: h });
  expect(g1.ok()).toBeTruthy();
  const d1 = await g1.json();
  expect(d1.stage).toBe("contacted");

  // Move to proposal
  const m2 = await request.post(`${BASE}/api/crm/deals/${deal.id}/move-stage`, {
    headers: h, data: { stage: "proposal" },
  });
  expect(m2.ok()).toBeTruthy();

  // Move to won
  const m3 = await request.post(`${BASE}/api/crm/deals/${deal.id}/move-stage`, {
    headers: h, data: { stage: "won" },
  });
  expect(m3.ok()).toBeTruthy();
  const d3 = await m3.json();
  expect(d3.stage).toBe("won");
  expect(d3.status).toBe("won");

  // Verify in deals list
  const list = await request.get(`${BASE}/api/crm/deals?status=won`, { headers: h });
  expect(list.ok()).toBeTruthy();
  const items = (await list.json()).items;
  const found = items.find((d: any) => d.id === deal.id);
  expect(found).toBeTruthy();
  expect(found.stage).toBe("won");

  // Invalid stage should fail
  const m4 = await request.post(`${BASE}/api/crm/deals/${deal.id}/move-stage`, {
    headers: h, data: { stage: "invalid_stage" },
  });
  expect(m4.status()).toBe(400);
});
