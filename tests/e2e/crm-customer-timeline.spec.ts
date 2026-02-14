import { test, expect } from "@playwright/test";

const BASE = "https://booking-suite-pro.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test("crm-customer-timeline: customer+deal+notes+isolation", async ({ request }) => {
  // Signup Tenant A
  const su = await request.post(`${BASE}/api/onboarding/signup`, {
    data: {
      company_name: `TL_${UID}`,
      admin_name: "Admin",
      email: `tl_${UID}@test.com`,
      password: "test123456",
      plan: "starter",
      billing_cycle: "monthly",
    },
  });
  expect(su.ok()).toBeTruthy();
  const { access_token: token } = await su.json();
  const h = { Authorization: `Bearer ${token}` };

  // 1) Create customer
  const cc = await request.post(`${BASE}/api/crm/customers`, {
    headers: h,
    data: {
      name: `Timeline Cust ${UID}`,
      type: "individual",
      contacts: [{ type: "email", value: `cust_${UID}@example.com`, is_primary: true }],
    },
  });
  expect(cc.ok()).toBeTruthy();
  const cust = await cc.json();
  const customerId = cust.id;

  // 2) Create deal linked to customer
  const cd = await request.post(`${BASE}/api/crm/deals`, {
    headers: h,
    data: { title: `TL Deal ${UID}`, amount: 8000, currency: "TRY", customer_id: customerId },
  });
  expect(cd.ok()).toBeTruthy();
  const deal = await cd.json();

  // 3) Customer detail
  const gd = await request.get(`${BASE}/api/crm/customers/${customerId}`, { headers: h });
  expect(gd.ok()).toBeTruthy();
  const custDetail = await gd.json();
  const custName = custDetail.name || custDetail.customer?.name || "";
  expect(custName).toContain("Timeline Cust");

  // 4) Create note on customer
  const nc = await request.post(`${BASE}/api/crm/notes`, {
    headers: h,
    data: { content: "Important note for timeline", entity_type: "customer", entity_id: customerId },
  });
  expect(nc.ok()).toBeTruthy();

  // 5) List notes for customer
  const nl = await request.get(`${BASE}/api/crm/notes?entity_type=customer&entity_id=${customerId}`, { headers: h });
  expect(nl.ok()).toBeTruthy();
  const notes = await nl.json();
  expect(notes.items.length).toBeGreaterThan(0);
  expect(notes.items[0].content).toContain("Important note");

  // 6) Deal visible for customer
  const dl = await request.get(`${BASE}/api/crm/deals?customer_id=${customerId}`, { headers: h });
  expect(dl.ok()).toBeTruthy();
  expect((await dl.json()).items.length).toBeGreaterThan(0);

  // 7) Move deal stage + note on deal
  await request.post(`${BASE}/api/crm/deals/${deal.id}/move-stage`, {
    headers: h, data: { stage: "contacted" },
  });
  await request.post(`${BASE}/api/crm/notes`, {
    headers: h,
    data: { content: "Follow-up note", entity_type: "deal", entity_id: deal.id },
  });
  const dnl = await request.get(`${BASE}/api/crm/notes?entity_type=deal&entity_id=${deal.id}`, { headers: h });
  expect(dnl.ok()).toBeTruthy();
  expect((await dnl.json()).items.length).toBeGreaterThan(0);

  // 8) Tenant isolation - other tenant can't see customer
  const su2 = await request.post(`${BASE}/api/onboarding/signup`, {
    data: {
      company_name: `Other_${UID}`,
      admin_name: "Other",
      email: `other_${UID}@test.com`,
      password: "test123456",
      plan: "starter",
      billing_cycle: "monthly",
    },
  });
  expect(su2.ok()).toBeTruthy();
  const t2 = await su2.json();
  const r = await request.get(`${BASE}/api/crm/customers/${customerId}`, {
    headers: { Authorization: `Bearer ${t2.access_token}` },
  });
  expect(r.status()).toBe(404);
});
