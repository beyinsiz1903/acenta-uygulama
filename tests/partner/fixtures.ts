// tests/partner/fixtures.ts
import { test as base, expect } from "@playwright/test";
import fs from "fs";
import path from "path";

type TenantAuth = {
  token: string;
  tenantId: string;
  baseURL?: string;
  email?: string;
};

function readTenantAuth(): TenantAuth {
  const p = path.join(process.cwd(), "tests", ".auth", "tenant.json");
  const raw = fs.readFileSync(p, "utf-8");
  const json = JSON.parse(raw);
  if (!json?.token || !json?.tenantId) {
    throw new Error("tests/.auth/tenant.json missing token or tenantId");
  }
  return json as TenantAuth;
}

export const test = base.extend({
  context: async ({ context }, use) => {
    const { token, tenantId } = readTenantAuth();

    await context.setExtraHTTPHeaders({
      Authorization: `Bearer ${token}`,
      "X-Tenant-Id": tenantId,
    });

    await use(context);
  },
});

export { expect };
