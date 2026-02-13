import { test, expect } from "@playwright/test";

const BASE = "https://nostalgic-ganguly-1.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test("crm-pipeline: deal lifecycle lead->contacted->proposal->won + task complete", async ({ request }) => {
  // Signup
  const su = await request.post(`${BASE}/api/onboarding/signup`, {
    data: {
      company_name: `PL_${UID}`,
      admin_name: "Admin",
      email: `pl_${UID}@test.com`,
      password: "test123456",
      plan: "starter",
      billing_cycle: "monthly",
    },
  });
  expect(su.ok()).toBeTruthy();
  const { access_token: token } = await su.json();
  const h = { Authorization: `Bearer ${token}` };

  // 1) Create deal in lead stage
  const cd = await request.post(`${BASE}/api/crm/deals`, {
    headers: h,
    data: { title: `E2E Deal ${UID}`, amount: 15000, currency: "TRY", stage: "lead" },
  });
  expect(cd.ok()).toBeTruthy();
  const deal = await cd.json();
  expect(deal.stage).toBe("lead");
  expect(deal.status).toBe("open");
  const dealId = deal.id;

  // 2) Move: lead -> contacted
  const m1 = await request.post(`${BASE}/api/crm/deals/${dealId}/move-stage`, {
    headers: h, data: { stage: "contacted" },
  });
  expect(m1.ok()).toBeTruthy();
  expect((await m1.json()).stage).toBe("contacted");

  // 3) Move: contacted -> proposal
  const m2 = await request.post(`${BASE}/api/crm/deals/${dealId}/move-stage`, {
    headers: h, data: { stage: "proposal" },
  });
  expect(m2.ok()).toBeTruthy();
  expect((await m2.json()).stage).toBe("proposal");

  // 4) Move: proposal -> won (status also changes)
  const m3 = await request.post(`${BASE}/api/crm/deals/${dealId}/move-stage`, {
    headers: h, data: { stage: "won" },
  });
  expect(m3.ok()).toBeTruthy();
  const won = await m3.json();
  expect(won.stage).toBe("won");
  expect(won.status).toBe("won");

  // 5) Create and complete task
  const ct = await request.post(`${BASE}/api/crm/tasks`, {
    headers: h, data: { title: `E2E Task ${UID}` },
  });
  expect(ct.ok()).toBeTruthy();
  const task = await ct.json();
  expect(task.status).toBe("open");

  const comp = await request.put(`${BASE}/api/crm/tasks/${task.id}/complete`, { headers: h });
  expect(comp.ok()).toBeTruthy();
  expect((await comp.json()).status).toBe("done");
});
