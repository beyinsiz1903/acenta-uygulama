// tests/auth/admin-subtree-guard.spec.ts
import { test, expect } from "@playwright/test";

// NOT: Bu testler, admin subtree (/app/admin/*) için UI guard davranışını doğrular.
// Backend RBAC zaten admin API'lerini koruyor; burada amaç route/guard regresyonlarını yakalamaktır.

const BASE_URL = "https://unified-control-4.preview.emergentagent.com";

async function login(page, email: string, password: string) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[data-testid="login-email"]', email);
  await page.fill('[data-testid="login-password"]', password);
  await page.click('[data-testid="login-submit"]');
  await page.waitForURL(/\/app\//, { timeout: 60000 });
}

// 1️⃣ agency1 -> /app/admin/agencies -> Unauthorized beklenir
test("agency user cannot access /app/admin/agencies", async ({ page }) => {
  await login(page, "agency1@acenta.test", "agency123");

  await page.goto(`${BASE_URL}/app/admin/agencies`);

  // URL admin subtree altında kalabilir, önemli olan içerik
  await expect(page.getByText(/Yetkiniz yok/i)).toBeVisible();

  // Admin başlığı görünmemeli (ör: "Acentalar" başlığı yok)
  const adminHeading = page.getByRole("heading", { name: /Acentalar/i });
  await expect(adminHeading).toHaveCount(0);

  // Ayrıca sidebar'da tipik bir admin menü öğesinin görünmediğini de kontrol edebiliriz
  const adminMenuLink = page.getByRole("link", { name: /Admin/ , exact: false });
  // Menü metinleri projeye göre değişebileceği için sadece yokluğunu soft şekilde kontrol ediyoruz
  await expect(adminMenuLink).toHaveCount(0);
});

// 2️⃣ admin@acenta.test -> /app/admin/agencies -> Admin heading görünür
// Not: Bu test, admin kullanıcının gerçekten super_admin/admin rolüne sahip olduğunu varsayar.
test("admin user can access /app/admin/agencies", async ({ page }) => {
  await login(page, "admin@acenta.test", "admin123");

  await page.goto(`${BASE_URL}/app/admin/agencies`);

  // Admin ekranı başlığının görünmesini bekliyoruz
  await expect(page.getByRole("heading", { name: /Acentalar/i })).toBeVisible();

  // Unauthorized metni olmamalı
  const unauthorized = page.getByText(/Yetkiniz yok/i);
  await expect(unauthorized).toHaveCount(0);
});
