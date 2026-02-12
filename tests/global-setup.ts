// tests/global-setup.ts
import { request, type FullConfig } from "@playwright/test";
import fs from "fs";
import path from "path";

export default async function globalSetup(_config: FullConfig) {
  const baseURL =
    process.env.PLAYWRIGHT_BASE_URL ??
    process.env.E2E_BASE_URL ??
    "https://conversational-ai-5.preview.emergentagent.com";

  const email = process.env.PLAYWRIGHT_EMAIL ?? "admin@acenta.test";
  const password = process.env.PLAYWRIGHT_PASSWORD ?? "admin123";

  const tenantId = process.env.PLAYWRIGHT_TENANT_ID;
  if (!tenantId) {
    throw new Error("PLAYWRIGHT_TENANT_ID is required (seeded tenant id).");
  }

  const rc = await request.newContext({ baseURL });

  const loginResp = await rc.post("/api/auth/login", {
    data: { email, password },
  });

  if (!loginResp.ok()) {
    throw new Error(`Login failed: ${loginResp.status()} ${await loginResp.text()}`);
  }

  const body = await loginResp.json();
  const token = (body as any)?.access_token as string | undefined;

  if (!token) {
    throw new Error("Login response did not include access_token");
  }

  const authDir = path.join(process.cwd(), "tests", ".auth");
  fs.mkdirSync(authDir, { recursive: true });

  const authPath = path.join(authDir, "tenant.json");
  fs.writeFileSync(
    authPath,
    JSON.stringify({ token, tenantId, baseURL, email }, null, 2),
    "utf-8"
  );

  await rc.dispose();
}
