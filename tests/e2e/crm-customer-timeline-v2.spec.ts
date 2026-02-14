import { test, expect } from "@playwright/test";

const BASE = "https://booking-suite-pro.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test("customer-timeline: aggregated feed with filters", async ({ request }) => {
  // Signup
  const su = await request.post(`${BASE}/api/onboarding/signup`, {
    data: { company_name: `TL2_${UID}`, admin_name: "Admin", email: `tl2_${UID}@test.com`, password: "test123456", plan: "starter", billing_cycle: "monthly" },
  });
  expect(su.ok()).toBeTruthy();
  const { access_token: token } = await su.json();
  const h = { Authorization: `Bearer ${token}` };

  // Create customer
  const cc = await request.post(`${BASE}/api/crm/customers`, {
    headers: h,
    data: { name: `TL2 Customer ${UID}`, type: "individual", contacts: [{ type: "email", value: `tl2_${UID}@x.com`, is_primary: true }] },
  });
  expect(cc.ok()).toBeTruthy();
  const cust = await cc.json();
  const cid = cust.id;

  // Create deal for customer
  await request.post(`${BASE}/api/crm/deals`, { headers: h, data: { title: `TL2 Deal ${UID}`, amount: 5000, currency: "TRY", customer_id: cid } });

  // Add note on customer
  await request.post(`${BASE}/api/crm/notes`, { headers: h, data: { content: "Timeline note", entity_type: "customer", entity_id: cid } });

  // GET timeline - all types
  const t1 = await request.get(`${BASE}/api/crm/customers/${cid}/timeline?limit=50`, { headers: h });
  expect(t1.ok()).toBeTruthy();
  const b1 = await t1.json();
  expect(b1.items.length).toBeGreaterThanOrEqual(2); // note + deal

  // Filter by notes
  const t2 = await request.get(`${BASE}/api/crm/customers/${cid}/timeline?filter_type=notes`, { headers: h });
  expect(t2.ok()).toBeTruthy();
  const b2 = await t2.json();
  expect(b2.items.length).toBeGreaterThanOrEqual(1);
  expect(b2.items.every((i: any) => i.type === "note")).toBe(true);

  // Filter by deals
  const t3 = await request.get(`${BASE}/api/crm/customers/${cid}/timeline?filter_type=deals`, { headers: h });
  expect(t3.ok()).toBeTruthy();
  const b3 = await t3.json();
  expect(b3.items.length).toBeGreaterThanOrEqual(1);
  expect(b3.items.every((i: any) => i.type === "deal")).toBe(true);

  // Filter by payments (should be empty)
  const t4 = await request.get(`${BASE}/api/crm/customers/${cid}/timeline?filter_type=payments`, { headers: h });
  expect(t4.ok()).toBeTruthy();
  const b4 = await t4.json();
  expect(b4.items.length).toBe(0); // no payments linked to customer

  // Verify tenant isolation
  const su2 = await request.post(`${BASE}/api/onboarding/signup`, {
    data: { company_name: `Other2_${UID}`, admin_name: "O", email: `oth2_${UID}@test.com`, password: "test123456", plan: "starter", billing_cycle: "monthly" },
  });
  const { access_token: t2tok } = await su2.json();
  const r = await request.get(`${BASE}/api/crm/customers/${cid}/timeline`, { headers: { Authorization: `Bearer ${t2tok}` } });
  // Should get 404 (customer not found in other tenant) or empty items
  const rb = await r.json();
  expect(rb.items?.length || 0).toBe(0);
});
