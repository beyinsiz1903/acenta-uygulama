const { chromium } = require('playwright');

async function debugAdminAccess() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Login as admin
    console.log('1. Going to login page...');
    await page.goto('https://travelpartner-2.preview.emergentagent.com/login');
    
    console.log('2. Filling login form...');
    await page.fill('[data-testid="login-email"]', 'admin@acenta.test');
    await page.fill('[data-testid="login-password"]', 'admin123');
    
    console.log('3. Submitting login...');
    await page.click('[data-testid="login-submit"]');
    
    // Wait for redirect
    await page.waitForURL(/\/app\//, { timeout: 60000 });
    console.log('4. Login successful, current URL:', page.url());
    
    // Navigate to admin agencies
    console.log('5. Navigating to admin agencies...');
    await page.goto('https://travelpartner-2.preview.emergentagent.com/app/admin/agencies');
    
    // Wait a bit for page to load
    await page.waitForTimeout(3000);
    
    console.log('6. Current URL after navigation:', page.url());
    console.log('7. Page title:', await page.title());
    
    // Get page content
    const bodyText = await page.textContent('body');
    console.log('8. Page content (first 500 chars):', bodyText.substring(0, 500));
    
    // Check for specific elements
    const unauthorizedText = await page.locator('text=/Yetkiniz yok/i').count();
    console.log('9. Unauthorized text count:', unauthorizedText);
    
    const contextMissingText = await page.locator('text=/Hesap bağlamı eksik/i').count();
    console.log('10. Context missing text count:', contextMissingText);
    
    const adminHeading = await page.locator('h1, h2, h3, h4, h5, h6').allTextContents();
    console.log('11. All headings:', adminHeading);
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

debugAdminAccess();