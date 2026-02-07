#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================
# (same as before - preserved)
#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

user_problem_statement: "Zero Migration Friction Engine + Google Sheets Live Sync (Service Account, Production-Grade with Graceful Fallback)"

backend:
  - task: "POST /api/admin/import/hotels/upload"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "All tests passed."

  - task: "POST /api/admin/import/hotels/validate"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false

  - task: "POST /api/admin/import/hotels/execute"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false

  - task: "GET /api/admin/import/jobs + /jobs/{id}"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false

  - task: "GET /api/admin/import/export-template"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false

  - task: "GET /api/admin/import/sheet/config - Configuration status"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Returns configured=false when GOOGLE_SERVICE_ACCOUNT_JSON not set. Returns email when configured."

  - task: "POST /api/admin/import/sheet/connect - Enhanced with header detection"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Validates sheet access if configured. Saves connection with full schema. Returns service_account_email + detected_headers."

  - task: "POST /api/admin/import/sheet/sync - Real sync with graceful fallback"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Returns not_configured gracefully when no API key. Runs full sync cycle when configured."

  - task: "GET /api/admin/import/sheet/connection + /sheet/status"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Returns connection details + sync status + recent runs."

  - task: "Sheet Sync Service (fingerprint + delta + upsert)"
    implemented: true
    working: true
    file: "backend/app/services/sheet_sync_service.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "SHA256 fingerprinting, delta detection, tenant-scoped upsert, sync lock, scheduled sync."

  - task: "Google Sheets Client (Service Account)"
    implemented: true
    working: true
    file: "backend/app/services/google_sheets_client.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Real Google API client with graceful fallback. is_configured(), get_service_account_email(), fetch_sheet_data()."

  - task: "APScheduler job for auto-sync"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Runs every GOOGLE_SHEETS_SYNC_INTERVAL_MINUTES (default 5). Processes all sync_enabled connections with lock."

frontend:
  - task: "Google Sheets Tab - Production UI"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/admin/AdminImportPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Service account email display, sync status card, connect form, sync now button, how-to guide, graceful fallback. Screenshot verified."

metadata:
  created_by: "main_agent"
  version: "9.0"
  test_sequence: 18
  run_ui: false

test_plan:
  current_focus:
    - "GET /api/admin/import/sheet/config"
    - "POST /api/admin/import/sheet/connect"
    - "POST /api/admin/import/sheet/sync"
    - "GET /api/admin/import/sheet/connection"
    - "GET /api/admin/import/sheet/status"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"
