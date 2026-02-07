#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================
# (same as before - preserved)
#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

user_problem_statement: "Portfolio Sync Engine — Multi-Hotel Google Sheets Sync (300 otel/300 sheet, on-demand + scheduler, graceful fallback)"

backend:
  - task: "GET /api/admin/sheets/config - Configuration status"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "POST /api/admin/sheets/connect - Connect hotel sheet"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "GET /api/admin/sheets/connections - List connections"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "GET /api/admin/sheets/connections/{hotel_id} - Single connection"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "PATCH /api/admin/sheets/connections/{hotel_id} - Update connection"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "DELETE /api/admin/sheets/connections/{hotel_id} - Delete connection"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "POST /api/admin/sheets/sync/{hotel_id} - Manual sync"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "POST /api/admin/sheets/sync-all - Sync all connections"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true

  - task: "GET /api/admin/sheets/status - Portfolio health dashboard"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "GET /api/admin/sheets/runs - Sync run history"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true

  - task: "GET /api/admin/sheets/stale-hotels - Stale connections"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true

  - task: "POST /api/admin/sheets/preview-mapping - Preview sheet mapping"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true

  - task: "GET /api/admin/sheets/available-hotels - Hotels for connect wizard"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true

  - task: "Auth Guards - All sheet endpoints require admin auth"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "Tenant Isolation - Queries scoped to tenant"
    implemented: true
    working: "untested"
    file: "backend/app/routers/admin_sheets.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "Graceful Fallback - System doesn't crash without API key"
    implemented: true
    working: "untested"
    file: "backend/app/services/sheets_provider.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

frontend:
  - task: "Portfolio Sync Page"
    implemented: false
    working: "NA"
    stuck_count: 0
    priority: "high"
    needs_retesting: false

metadata:
  created_by: "main_agent"
  version: "11.0"
  test_sequence: 20
  run_ui: false

test_plan:
  current_focus: ["GET /api/admin/sheets/config", "POST /api/admin/sheets/connect", "GET /api/admin/sheets/connections", "POST /api/admin/sheets/sync/{hotel_id}", "GET /api/admin/sheets/status", "Auth Guards", "Tenant Isolation", "Graceful Fallback"]
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: "Phase 1 Backend: Portfolio Sync Engine implemented with new router /api/admin/sheets/*, new services (sheets_provider.py, hotel_portfolio_sync_service.py), new collections (hotel_portfolio_sources, sheet_sync_runs, hotel_inventory_snapshots). All endpoints follow existing auth/RBAC/audit patterns. Graceful fallback when GOOGLE_SERVICE_ACCOUNT_JSON is not set. Please test all new endpoints."
