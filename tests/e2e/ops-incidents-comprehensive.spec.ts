import { test, expect } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "muratsutay@hotmail.com";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "murat1903";

async function loginAsSuperAdmin(page) {
  await page.goto(`${BASE_URL}/login`);

  const emailInput = page.getByTestId("login-email");
  const passwordInput = page.getByTestId("login-password");
  const submitButton = page.getByTestId("login-submit");

  await emailInput.fill(ADMIN_EMAIL);
  await passwordInput.fill(ADMIN_PASSWORD);

  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    submitButton.click(),
  ]);
}

test.describe("Ops Incidents Console v2 - Comprehensive Testing", () => {
  
  test("filter combinations and query parameter validation", async ({ page }) => {
    await loginAsSuperAdmin(page);

    let lastRequestUrl: string | null = null;
    let requestCount = 0;

    // Intercept API calls to verify query parameters
    await page.route("**/api/admin/ops/incidents**", async (route) => {
      const url = new URL(route.request().url());
      lastRequestUrl = url.toString();
      requestCount++;

      // Always verify include_supplier_health=true is present
      const includeHealth = url.searchParams.get("include_supplier_health");
      expect(includeHealth).toBe("true");

      const mockResponse = {
        total: 2,
        items: [
          {
            incident_id: "inc_filter_test_1",
            type: "risk_review",
            severity: "high",
            status: "open",
            summary: "Test incident for filters",
            created_at: "2026-02-03T10:00:00Z",
            source_ref: { booking_id: "bkg_test_1" },
            supplier_health: {
              supplier_code: "mock",
              circuit_state: "closed",
              notes: []
            }
          }
        ]
      };

      await route.fulfill({ json: mockResponse });
    });

    await page.goto(`${BASE_URL}/app/ops/incidents`);

    // Wait for initial load
    await expect(page.getByTestId("ops-incidents-table")).toBeVisible();
    await page.waitForTimeout(500);

    // Test 1: Status + Severity combination
    console.log("Testing status + severity filter combination...");
    
    // Set status to "resolved"
    await page.getByTestId("ops-incidents-filter-status").click();
    await page.getByRole("option", { name: "Resolved" }).click();
    await page.waitForTimeout(300);

    // Set severity to "critical"
    await page.getByTestId("ops-incidents-filter-severity").click();
    await page.getByRole("option", { name: "critical" }).click();
    await page.waitForTimeout(300);

    // Verify both parameters are in the URL
    expect(lastRequestUrl).not.toBeNull();
    if (lastRequestUrl) {
      const url = new URL(lastRequestUrl);
      expect(url.searchParams.get("status")).toBe("resolved");
      expect(url.searchParams.get("severity")).toBe("critical");
      expect(url.searchParams.get("include_supplier_health")).toBe("true");
    }

    // Test 2: Type + Status + Severity combination
    console.log("Testing type + status + severity filter combination...");
    
    await page.getByTestId("ops-incidents-filter-type").click();
    await page.getByRole("option", { name: "supplier_partial_failure" }).click();
    await page.waitForTimeout(300);

    // Verify all three parameters are in the URL
    expect(lastRequestUrl).not.toBeNull();
    if (lastRequestUrl) {
      const url = new URL(lastRequestUrl);
      expect(url.searchParams.get("type")).toBe("supplier_partial_failure");
      expect(url.searchParams.get("status")).toBe("resolved");
      expect(url.searchParams.get("severity")).toBe("critical");
      expect(url.searchParams.get("include_supplier_health")).toBe("true");
    }

    // Test 3: Reset to "all" should remove parameters
    console.log("Testing filter reset to 'all' removes query parameters...");
    
    await page.getByTestId("ops-incidents-filter-type").click();
    await page.getByRole("option", { name: "All" }).click();
    await page.waitForTimeout(300);

    if (lastRequestUrl) {
      const url = new URL(lastRequestUrl);
      expect(url.searchParams.get("type")).toBeNull();
      expect(url.searchParams.get("include_supplier_health")).toBe("true");
    }

    console.log(`Total API requests made: ${requestCount}`);
  });

  test("empty state and clear filters functionality", async ({ page }) => {
    await loginAsSuperAdmin(page);

    let clearFiltersClicked = false;

    // Mock empty response
    await page.route("**/api/admin/ops/incidents**", async (route) => {
      const url = new URL(route.request().url());
      
      // Return empty results
      const emptyResponse = {
        total: 0,
        items: []
      };

      await route.fulfill({ json: emptyResponse });
    });

    await page.goto(`${BASE_URL}/app/ops/incidents`);

    // Wait for page to load
    await expect(page.getByTestId("ops-incidents-table")).toBeVisible();
    await page.waitForTimeout(500);

    // Apply some filters first
    console.log("Applying filters to trigger empty state with clear button...");
    
    await page.getByTestId("ops-incidents-filter-status").click();
    await page.getByRole("option", { name: "Resolved" }).click();
    await page.waitForTimeout(300);

    await page.getByTestId("ops-incidents-filter-type").click();
    await page.getByRole("option", { name: "risk_review" }).click();
    await page.waitForTimeout(300);

    // Verify empty state is shown
    await expect(page.getByText("No incidents")).toBeVisible();
    await expect(page.getByText("There are no ops incidents for the selected filters.")).toBeVisible();

    // Verify clear filters button is present and clickable
    const clearFiltersButton = page.getByRole("button", { name: "Clear filters" });
    await expect(clearFiltersButton).toBeVisible();

    // Click clear filters button
    console.log("Clicking clear filters button...");
    await clearFiltersButton.click();
    clearFiltersClicked = true;

    // Verify filters are reset
    await page.waitForTimeout(300);
    
    // Check that filter selectors show "All" or default values
    const statusFilter = page.getByTestId("ops-incidents-filter-status");
    const typeFilter = page.getByTestId("ops-incidents-filter-type");
    
    // The filters should be reset - we can verify by checking if the clear button disappears
    // (since no filters are active anymore)
    await expect(clearFiltersButton).not.toBeVisible();

    console.log(`Clear filters functionality tested: ${clearFiltersClicked}`);
  });

  test("loading skeleton state", async ({ page }) => {
    await loginAsSuperAdmin(page);

    let requestResolved = false;

    // Mock delayed response to test loading state
    await page.route("**/api/admin/ops/incidents**", async (route) => {
      // Delay response to see loading state
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const mockResponse = {
        total: 1,
        items: [
          {
            incident_id: "inc_loading_test",
            type: "supplier_partial_failure",
            severity: "medium",
            status: "open",
            summary: "Loading test incident",
            created_at: "2026-02-03T10:00:00Z",
            source_ref: { session_id: "sess_loading" },
            supplier_health: {
              supplier_code: "mock",
              circuit_state: "closed",
              notes: []
            }
          }
        ]
      };

      requestResolved = true;
      await route.fulfill({ json: mockResponse });
    });

    await page.goto(`${BASE_URL}/app/ops/incidents`);

    console.log("Testing loading skeleton state...");

    // Verify loading spinner is visible in the header
    await expect(page.locator(".animate-spin")).toBeVisible({ timeout: 1000 });

    // Verify skeleton rows are visible (5 skeleton rows as per implementation)
    const skeletonRows = page.locator(".animate-pulse");
    await expect(skeletonRows).toHaveCount(5, { timeout: 1000 });

    // Verify skeleton elements have proper structure
    const firstSkeletonRow = skeletonRows.first();
    await expect(firstSkeletonRow).toBeVisible();

    // Wait for loading to complete
    await page.waitForTimeout(3000);
    
    // Verify loading state is gone and real content is shown
    await expect(page.locator(".animate-spin")).not.toBeVisible();
    await expect(page.getByTestId("ops-incidents-rows")).toBeVisible();

    console.log(`Loading skeleton state tested successfully. Request resolved: ${requestResolved}`);
  });

  test("error state handling", async ({ page }) => {
    await loginAsSuperAdmin(page);

    let errorResponseSent = false;

    // Mock error responses
    await page.route("**/api/admin/ops/incidents**", async (route) => {
      console.log("Mocking 500 error response...");
      errorResponseSent = true;
      
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            message: "Internal server error",
            code: "INTERNAL_ERROR"
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/app/ops/incidents`);

    console.log("Testing error state handling...");

    // Wait for error state to appear
    await page.waitForTimeout(2000);

    // Verify error state is displayed
    // The ErrorState component should be visible with the error message
    const errorElement = page.locator("text=Internal server error").or(
      page.locator("text=An error occurred").or(
        page.locator("text=Error")
      )
    );
    
    await expect(errorElement.first()).toBeVisible({ timeout: 5000 });

    // Verify that the page doesn't crash and maintains structure
    await expect(page.getByTestId("ops-incidents-table")).toBeVisible();

    // Verify no incidents rows are shown during error state
    await expect(page.getByTestId("ops-incidents-rows")).not.toBeVisible();

    console.log(`Error state handled successfully. Error response sent: ${errorResponseSent}`);
  });

  test("403 forbidden error handling", async ({ page }) => {
    await loginAsSuperAdmin(page);

    // Mock 403 response
    await page.route("**/api/admin/ops/incidents**", async (route) => {
      console.log("Mocking 403 forbidden response...");
      
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            message: "Access forbidden",
            code: "FORBIDDEN"
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/app/ops/incidents`);

    console.log("Testing 403 forbidden error handling...");

    // Wait for error state
    await page.waitForTimeout(2000);

    // Verify error handling - should show error state, not crash
    const errorElement = page.locator("text=Access forbidden").or(
      page.locator("text=Forbidden").or(
        page.locator("text=Error")
      )
    );
    
    await expect(errorElement.first()).toBeVisible({ timeout: 5000 });

    // Page should still be functional
    await expect(page.getByTestId("ops-incidents-table")).toBeVisible();

    console.log("403 error handled successfully");
  });

  test("supplier health badge states comprehensive", async ({ page }) => {
    await loginAsSuperAdmin(page);

    // Mock response with all supplier health states
    await page.route("**/api/admin/ops/incidents**", async (route) => {
      const comprehensiveResponse = {
        total: 4,
        items: [
          {
            incident_id: "inc_health_1",
            type: "supplier_partial_failure",
            severity: "critical",
            status: "open",
            summary: "Circuit OPEN test",
            created_at: "2026-02-03T10:00:00Z",
            source_ref: { session_id: "sess_1" },
            supplier_health: {
              supplier_code: "paximum",
              circuit_state: "open",
              notes: []
            }
          },
          {
            incident_id: "inc_health_2",
            type: "supplier_all_failed",
            severity: "high",
            status: "open",
            summary: "No health test",
            created_at: "2026-02-03T09:50:00Z",
            source_ref: { session_id: "sess_2" },
            supplier_health: {
              supplier_code: "mock",
              notes: ["health_not_found"]
            }
          },
          {
            incident_id: "inc_health_3",
            type: "risk_review",
            severity: "medium",
            status: "resolved",
            summary: "Circuit CLOSED test",
            created_at: "2026-02-03T09:40:00Z",
            source_ref: { booking_id: "bkg_123" },
            supplier_health: {
              supplier_code: "mock",
              circuit_state: "closed",
              notes: []
            }
          },
          {
            incident_id: "inc_health_4",
            type: "risk_review",
            severity: "low",
            status: "open",
            summary: "No supplier health",
            created_at: "2026-02-03T09:30:00Z",
            source_ref: { booking_id: "bkg_456" }
            // No supplier_health field
          }
        ]
      };

      await route.fulfill({ json: comprehensiveResponse });
    });

    await page.goto(`${BASE_URL}/app/ops/incidents`);

    console.log("Testing comprehensive supplier health badge states...");

    // Wait for table to load
    await expect(page.getByTestId("ops-incidents-table")).toBeVisible();
    await page.waitForTimeout(1000);

    // Test all badge states
    console.log("Verifying Circuit: OPEN badge...");
    await expect(page.getByTestId("ops-incidents-health-open")).toBeVisible();

    console.log("Verifying NO HEALTH badge...");
    await expect(page.getByTestId("ops-incidents-health-no-health")).toBeVisible();

    console.log("Verifying Circuit: CLOSED badge...");
    await expect(page.getByTestId("ops-incidents-health-closed")).toBeVisible();

    // Test tooltips
    console.log("Testing tooltips...");
    
    // Hover over NO HEALTH badge to see tooltip
    const noHealthBadge = page.getByTestId("ops-incidents-health-no-health");
    await noHealthBadge.hover();
    await expect(page.getByText("Health snapshot not found (fail-open).")).toBeVisible({ timeout: 2000 });

    // Hover over CLOSED badge to see tooltip
    const closedBadge = page.getByTestId("ops-incidents-health-closed");
    await closedBadge.hover();
    await expect(page.getByText("Circuit is closed; supplier is allowed for routing.")).toBeVisible({ timeout: 2000 });

    console.log("All supplier health badge states tested successfully");
  });

  test("incident detail drawer comprehensive", async ({ page }) => {
    await loginAsSuperAdmin(page);

    // Mock list response
    await page.route("**/api/admin/ops/incidents**", async (route) => {
      const listResponse = {
        total: 1,
        items: [
          {
            incident_id: "inc_detail_test",
            type: "risk_review",
            severity: "high",
            status: "open",
            summary: "Detailed incident test",
            created_at: "2026-02-03T10:00:00Z",
            source_ref: { booking_id: "bkg_detail_test" },
            supplier_health: {
              supplier_code: "paximum",
              circuit_state: "open",
              notes: []
            }
          }
        ]
      };

      await route.fulfill({ json: listResponse });
    });

    // Mock detail response
    await page.route("**/api/admin/ops/incidents/inc_detail_test**", async (route) => {
      const detailResponse = {
        incident_id: "inc_detail_test",
        organization_id: "org_test",
        type: "risk_review",
        severity: "high",
        status: "open",
        summary: "Comprehensive detail test incident with all fields populated",
        source_ref: {
          booking_id: "bkg_detail_test",
          session_id: "sess_detail_test",
          offer_token: "offer_token_123",
          supplier_code: "paximum",
          risk_decision: "review_required"
        },
        meta: {
          risk_score: 0.85,
          factors: ["high_amount", "new_customer"],
          review_reason: "Amount exceeds threshold"
        },
        created_at: "2026-02-03T10:00:00Z",
        updated_at: "2026-02-03T10:05:00Z",
        resolved_at: null,
        resolved_by_user_id: null,
        supplier_health: {
          supplier_code: "paximum",
          window_sec: 900,
          success_rate: 0.15,
          error_rate: 0.85,
          avg_latency_ms: 1200,
          p95_latency_ms: 3000,
          last_error_codes: ["TIMEOUT", "CONNECTION_ERROR"],
          circuit_state: "open",
          circuit_until: "2026-02-03T10:15:00Z",
          consecutive_failures: 5,
          updated_at: "2026-02-03T10:05:00Z",
          notes: ["performance_degraded"]
        }
      };

      await route.fulfill({ json: detailResponse });
    });

    await page.goto(`${BASE_URL}/app/ops/incidents`);

    console.log("Testing comprehensive incident detail drawer...");

    // Wait for table and click on row
    await expect(page.getByTestId("ops-incidents-table")).toBeVisible();
    await page.waitForTimeout(1000);

    const firstRow = page.getByTestId("ops-incidents-row").first();
    await expect(firstRow).toBeVisible();
    await firstRow.click();

    // Verify drawer opens
    const drawer = page.getByTestId("ops-incident-drawer");
    await expect(drawer).toBeVisible({ timeout: 5000 });

    console.log("Verifying drawer content...");

    // Verify meta fields
    await expect(page.getByText("Type: risk_review")).toBeVisible();
    await expect(page.getByText("Severity: high")).toBeVisible();
    await expect(page.getByText("Status: open")).toBeVisible();

    // Verify source_ref fields
    await expect(page.getByText("Booking: bkg_detail_test")).toBeVisible();
    await expect(page.getByText("Session: sess_detail_test")).toBeVisible();
    await expect(page.getByText("Offer token: offer_token_123")).toBeVisible();
    await expect(page.getByText("Supplier code: paximum")).toBeVisible();
    await expect(page.getByText("Risk decision: review_required")).toBeVisible();

    // Verify summary
    await expect(page.getByText("Comprehensive detail test incident with all fields populated")).toBeVisible();

    // Verify supplier health panel
    const healthPanel = page.getByTestId("ops-incident-drawer-health");
    await expect(healthPanel).toBeVisible();

    console.log("Verifying supplier health details...");
    
    // Verify health metrics
    await expect(page.getByText("Success rate: 15%")).toBeVisible();
    await expect(page.getByText("Error rate: 85%")).toBeVisible();
    await expect(page.getByText("Avg latency: 1200 ms")).toBeVisible();
    await expect(page.getByText("p95 latency: 3000 ms")).toBeVisible();
    await expect(page.getByText("Last error codes: TIMEOUT, CONNECTION_ERROR")).toBeVisible();

    // Verify meta JSON dump
    await expect(page.getByText('"risk_score": 0.85')).toBeVisible();

    // Test drawer close
    console.log("Testing drawer close functionality...");
    const closeButton = page.locator('[data-testid="ops-incident-drawer"] button').first();
    await closeButton.click();
    await expect(drawer).not.toBeVisible();

    console.log("Incident detail drawer comprehensive test completed successfully");
  });
});