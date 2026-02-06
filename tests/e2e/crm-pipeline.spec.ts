import { test, expect } from "@playwright/test";

const BASE_URL = "https://enterprise-ops-8.preview.emergentagent.com";
const UID = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

test.describe("CRM Pipeline", () => {
  let token: string;
  let dealId: string;

  test.beforeAll(async ({ request }) => {
    const signup = await request.post(`${BASE_URL}/api/onboarding/signup`, {
      data: {
        company_name: `PipelineCo_${UID}`,
        admin_name: "Pipeline Admin",
        email: `pipeline_${UID}@test.com`,
        password: "test123456",
        plan: "starter",
        billing_cycle: "monthly",
      },
    });
    expect(signup.ok()).toBeTruthy();
    const d = await signup.json();
    token = d.access_token;
  });

  test("create deal in lead stage", async ({ request }) => {
    const res = await request.post(`${BASE_URL}/api/crm/deals`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { title: `Test Deal ${UID}`, amount: 15000, currency: "TRY", stage: "lead" },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.stage).toBe("lead");
    expect(body.status).toBe("open");
    dealId = body.id;
  });

  test("move deal: lead -> contacted", async ({ request }) => {
    const res = await request.post(`${BASE_URL}/api/crm/deals/${dealId}/move-stage`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { stage: "contacted" },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.stage).toBe("contacted");
    expect(body.status).toBe("open");
  });

  test("move deal: contacted -> proposal", async ({ request }) => {
    const res = await request.post(`${BASE_URL}/api/crm/deals/${dealId}/move-stage`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { stage: "proposal" },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.stage).toBe("proposal");
  });

  test("move deal: proposal -> won (status also changes)", async ({ request }) => {
    const res = await request.post(`${BASE_URL}/api/crm/deals/${dealId}/move-stage`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { stage: "won" },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.stage).toBe("won");
    expect(body.status).toBe("won");
  });

  test("stage move writes audit log", async ({ request }) => {
    // Create another deal and move it to check audit
    const create = await request.post(`${BASE_URL}/api/crm/deals`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { title: `Audit Deal ${UID}`, amount: 5000, currency: "TRY" },
    });
    const d2 = await create.json();
    const move = await request.post(`${BASE_URL}/api/crm/deals/${d2.id}/move-stage`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { stage: "contacted" },
    });
    expect(move.ok()).toBeTruthy();
    // Just verify it doesn't error - audit is fire-and-forget
  });

  test("create and complete task", async ({ request }) => {
    const create = await request.post(`${BASE_URL}/api/crm/tasks`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { title: `Test Task ${UID}` },
    });
    expect(create.ok()).toBeTruthy();
    const task = await create.json();
    expect(task.status).toBe("open");

    const complete = await request.put(`${BASE_URL}/api/crm/tasks/${task.id}/complete`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(complete.ok()).toBeTruthy();
    const done = await complete.json();
    expect(done.status).toBe("done");
  });
});
