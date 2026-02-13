// tests/e2e/login-test.spec.ts
import { test, expect } from "@playwright/test";

const BASE_URL = "https://test-data-populator.preview.emergentagent.com";

test.describe("Login Functionality Test", () => {
  test("login process with debug information", async ({ page }) => {
    console.log("Starting login test");
    
    // Navigate to login page
    await page.goto(`${BASE_URL}/login`);
    console.log("Loaded login page");
    await page.waitForLoadState("networkidle");
    
    // Take screenshot of login form
    await page.screenshot({ path: 'login-page.png', fullPage: true });
    console.log("Login page screenshot captured");
    
    // Fill login form
    await page.fill('[data-testid="login-email"]', 'admin@acenta.test');
    await page.fill('[data-testid="login-password"]', 'admin123');
    console.log("Filled login form");
    
    // Set up network request listener
    page.on('request', request => {
      if (request.url().includes('/api/auth/login')) {
        console.log('Login request:', request.url());
        console.log('Login request method:', request.method());
      }
    });
    
    page.on('response', async response => {
      if (response.url().includes('/api/auth/login')) {
        console.log('Login response status:', response.status());
        try {
          const body = await response.json();
          console.log('Login response body:', JSON.stringify(body, null, 2));
        } catch (e) {
          console.log('Failed to parse response body');
        }
      }
    });
    
    // Click login button and capture result
    await page.click('[data-testid="login-submit"]');
    console.log("Clicked login button");
    
    // Wait a bit to see response
    await page.waitForTimeout(5000);
    
    // Check current URL
    const currentUrl = page.url();
    console.log("Current URL after login attempt:", currentUrl);
    
    // Take screenshot after login attempt
    await page.screenshot({ path: 'after-login.png', fullPage: true });
    console.log("After-login screenshot captured");
    
    // Log page content
    console.log("Page content:", await page.content());
  });
});