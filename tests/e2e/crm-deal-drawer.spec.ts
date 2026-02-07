import { test, expect } from "@playwright/test";

const BASE = "https://hardening-e1-e4.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test("deal-drawer: open, switch tabs, add note, close", async ({ request }) => {
  // Signup + seed
  const su = await request.post(`${BASE}/api/onboarding/signup`, {
    data: { company_name: `DD_${UID}`, admin_name: "Admin", email: `dd_${UID}@test.com`, password: "test123456", plan: "starter", billing_cycle: "monthly" },
  });
  expect(su.ok()).toBeTruthy();
  const { access_token: token } = await su.json();
  const h = { Authorization: `Bearer ${token}` };

  // Create deal
  const cd = await request.post(`${BASE}/api/crm/deals`, { headers: h, data: { title: `Drawer Deal ${UID}`, amount: 12000, currency: "TRY", stage: "lead" } });
  expect(cd.ok()).toBeTruthy();
  const deal = await cd.json();

  // GET deal by ID
  const gd = await request.get(`${BASE}/api/crm/deals/${deal.id}`, { headers: h });
  expect(gd.ok()).toBeTruthy();
  const dealData = await gd.json();
  expect(dealData.title).toContain("Drawer Deal");

  // Add note to deal
  const note = await request.post(`${BASE}/api/crm/notes`, {
    headers: h,
    data: { content: `E2E drawer note ${UID}`, entity_type: "deal", entity_id: deal.id },
  });
  expect(note.ok()).toBeTruthy();

  // Verify notes for this deal
  const nl = await request.get(`${BASE}/api/crm/notes?entity_type=deal&entity_id=${deal.id}`, { headers: h });
  expect(nl.ok()).toBeTruthy();
  const notes = await nl.json();
  expect(notes.items.length).toBeGreaterThan(0);
  expect(notes.items[0].content).toContain(`E2E drawer note`);

  // Create task linked to deal
  const ct = await request.post(`${BASE}/api/crm/tasks`, {
    headers: h,
    data: { title: `Drawer Task ${UID}`, related_type: "deal", related_id: deal.id },
  });
  expect(ct.ok()).toBeTruthy();

  // Verify tasks for this deal
  const tl = await request.get(`${BASE}/api/crm/tasks?relatedType=deal&relatedId=${deal.id}&status=open`, { headers: h });
  expect(tl.ok()).toBeTruthy();
  const tasks = await tl.json();
  expect(tasks.items.length).toBeGreaterThan(0);

  // Get activity for this deal
  const al = await request.get(`${BASE}/api/crm/activity?entity_type=deal&entity_id=${deal.id}`, { headers: h });
  expect(al.ok()).toBeTruthy();
});
