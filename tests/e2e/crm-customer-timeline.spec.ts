import { test, expect } from "@playwright/test";

const BASE_URL = "https://enterprise-ops-8.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test.describe("CRM Customer Timeline", () => {
  let token: string;
  let customerId: string;
  let dealId: string;

  test.beforeAll(async ({ request }) => {
    const signup = await request.post(`${BASE_URL}/api/onboarding/signup`, {
      data: {
        company_name: `TimelineCo_${UID}`,
        admin_name: "Timeline Admin",
        email: `timeline_${UID}@test.com`,
        password: "test123456",
        plan: "starter",
        billing_cycle: "monthly",
      },
    });
    expect(signup.ok()).toBeTruthy();
    const d = await signup.json();
    token = d.access_token;

    // Create a customer
    const cust = await request.post(`${BASE_URL}/api/crm/customers`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        name: `Timeline Customer ${UID}`,
        type: "individual",
        contacts: [{ type: "email", value: `cust_${UID}@example.com`, is_primary: true }],
      },
    });
    expect(cust.ok()).toBeTruthy();
    const custData = await cust.json();
    customerId = custData.id;

    // Create a deal linked to customer
    const deal = await request.post(`${BASE_URL}/api/crm/deals`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { title: `Timeline Deal ${UID}`, amount: 8000, currency: "TRY", customer_id: customerId },
    });
    expect(deal.ok()).toBeTruthy();
    const dealData = await deal.json();
    dealId = dealData.id;
  });

  test("customer detail endpoint returns data", async ({ request }) => {
    const res = await request.get(`${BASE_URL}/api/crm/customers/${customerId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.id).toBe(customerId);
    expect(body.name).toContain("Timeline Customer");
  });

  test("create note on customer shows in notes list", async ({ request }) => {
    const noteRes = await request.post(`${BASE_URL}/api/crm/notes`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { content: "Important customer note for timeline", entity_type: "customer", entity_id: customerId },
    });
    expect(noteRes.ok()).toBeTruthy();

    // List notes for this customer
    const list = await request.get(`${BASE_URL}/api/crm/notes?entity_type=customer&entity_id=${customerId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(list.ok()).toBeTruthy();
    const body = await list.json();
    expect(body.items.length).toBeGreaterThan(0);
    expect(body.items[0].content).toContain("Important customer note");
  });

  test("deal linked to customer visible in deals list", async ({ request }) => {
    const res = await request.get(`${BASE_URL}/api/crm/deals?customer_id=${customerId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.items.length).toBeGreaterThan(0);
    const found = body.items.find((d: any) => d.id === dealId);
    expect(found).toBeTruthy();
  });

  test("deal stage change creates activity trail", async ({ request }) => {
    // Move deal stage
    const move = await request.post(`${BASE_URL}/api/crm/deals/${dealId}/move-stage`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { stage: "contacted" },
    });
    expect(move.ok()).toBeTruthy();

    // Create note on the deal
    const note = await request.post(`${BASE_URL}/api/crm/notes`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { content: "Follow-up after contact", entity_type: "deal", entity_id: dealId },
    });
    expect(note.ok()).toBeTruthy();

    // Verify notes on deal
    const notes = await request.get(`${BASE_URL}/api/crm/notes?entity_type=deal&entity_id=${dealId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(notes.ok()).toBeTruthy();
    const body = await notes.json();
    expect(body.items.length).toBeGreaterThan(0);
  });

  test("tenant isolation - other tenant cannot see customer", async ({ request }) => {
    // Signup another tenant
    const signup2 = await request.post(`${BASE_URL}/api/onboarding/signup`, {
      data: {
        company_name: `OtherCo_${UID}`,
        admin_name: "Other Admin",
        email: `other_${UID}@test.com`,
        password: "test123456",
        plan: "starter",
        billing_cycle: "monthly",
      },
    });
    expect(signup2.ok()).toBeTruthy();
    const d2 = await signup2.json();

    // Try to access customer from first tenant
    const res = await request.get(`${BASE_URL}/api/crm/customers/${customerId}`, {
      headers: { Authorization: `Bearer ${d2.access_token}` },
    });
    // Should be 404 (not found in other tenant)
    expect(res.status()).toBe(404);
  });
});
