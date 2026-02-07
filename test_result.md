#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
# ## user_problem_statement: {problem_statement}
# ## backend:
# ##   - task: "Task name"
# ##     implemented: true
# ##     working: true  # or false or "NA"
# ##     file: "file_path.py"
# ##     stuck_count: 0
# ##     priority: "high"  # or "medium" or "low"
# ##     needs_retesting: true
# ##     status_history:
# ##         -working: true  # or false or "NA"
# ##         -agent: "main"  # or "testing" or "user"
# ##         -comment: "Detailed comment about status"
# ##
# ## frontend:
# ##   - task: "Task name"
# ##     implemented: true
# ##     working: true  # or false or "NA"
# ##     file: "file_path.js"
# ##     stuck_count: 0
# ##     priority: "high"  # or "medium" or "low"
# ##     needs_retesting: true
# ##     status_history:
# ##         -working: true  # or false or "NA"
# ##         -agent: "main"  # or "testing" or "user"
# ##         -comment: "Detailed comment about status"
# ##
# ## metadata:
# ##   created_by: "main_agent"
# ##   version: "1.0"
# ##   test_sequence: 0
# ##   run_ui: false
# ##
# ## test_plan:
# ##   current_focus:
# ##     - "Task name 1"
# ##     - "Task name 2"
# ##   stuck_tasks:
# ##     - "Task name with persistent issues"
# ##   test_all: false
# ##   test_priority: "high_first"  # or "sequential" or "stuck_first"
#
# Incorporate User Feedback:
# When the user provides feedback on test results or identifies issues:
# 1. Update the status_history with the user's feedback
# 2. If the user marks something as not working, set needs_retesting: true
# 3. Prioritize fixing issues identified by the user
#
#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

user_problem_statement: "Zero Migration Friction Engine: Excel/CSV hotel import with column mapping, validation, bulk insert, image downloading, Google Sheets sync (MOCKED), import job tracking, and audit log."

backend:
  - task: "POST /api/admin/import/hotels/upload - Upload CSV/XLSX"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Accepts CSV/XLSX, parses headers+rows, creates import_job, returns preview (first 20 rows). Auto-detects mapping. Tested with 3-row CSV."
      - working: true
        agent: "testing"
        comment: "✅ COMPREHENSIVE TESTING PASSED: CSV upload works perfectly. Returns correct job_id, filename, total_rows, headers, preview, available_fields. File validation works (rejects .txt files). Authentication required (401 without token). Tested with 5-row CSV containing validation scenarios."

  - task: "POST /api/admin/import/hotels/validate - Validate with mapping"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Validates all rows with column mapping. Checks name required, city required, duplicates, price numeric. Returns valid/error counts."
      - working: true
        agent: "testing"
        comment: "✅ COMPREHENSIVE TESTING PASSED: Validation works perfectly. Correctly identified 3 valid rows, 2 errors (missing city, invalid price). Column mapping accurate. Duplicate detection works. Returns proper error messages in Turkish. Error handling for invalid job_id works (404)."

  - task: "POST /api/admin/import/hotels/execute - Bulk import"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Background task. Bulk inserts in batches of 100. Downloads images async. Updates job status. Tested: 3 hotels imported successfully."
      - working: true
        agent: "testing"
        comment: "✅ COMPREHENSIVE TESTING PASSED: Execute works perfectly. Background processing successful. Job status updates correctly from 'processing' to 'completed'. Successfully imported 3 valid hotels. Error handling for invalid job_id works (404). No valid rows error handling works properly."

  - task: "GET /api/admin/import/jobs - List import jobs"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Returns import jobs for org, sorted by created_at desc."
      - working: true
        agent: "testing"
        comment: "✅ COMPREHENSIVE TESTING PASSED: Job listing works perfectly. Returns array of jobs for organization. Includes all required fields (id, status, filename, total_rows, success_count, error_count, timestamps). Authentication required (401 without token). Sorting by created_at desc verified."

  - task: "GET /api/admin/import/jobs/{job_id} - Job detail + errors"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Returns job detail with errors array. Tested: status=completed, success_count=3, error_count=0."
      - working: true
        agent: "testing"
        comment: "✅ COMPREHENSIVE TESTING PASSED: Job detail works perfectly. Returns complete job info with errors array. Includes all required fields (id, status, success_count, error_count, errors). Error details include row_number, field, message. 404 handling for invalid job_id works correctly."

  - task: "GET /api/admin/import/export-template - XLSX template download"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Returns XLSX file with sample headers and 2 example rows."
      - working: true
        agent: "testing"
        comment: "✅ COMPREHENSIVE TESTING PASSED: Template export works perfectly. Returns proper XLSX file with correct content-type (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet) and content-disposition (attachment). Authentication required. File structure verified."

  - task: "POST /api/admin/import/sheet/connect - Google Sheet connection (MOCKED)"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "MOCKED. Stores connection in sheet_connections collection. Returns saved doc."
      - working: true
        agent: "testing"
        comment: "✅ COMPREHENSIVE TESTING PASSED: Google Sheets connection (MOCKED) works perfectly. Creates sheet_connections record with all required fields (id, sheet_id, worksheet_name, status). Returns saved document. Authentication required. Properly marked as MOCKED functionality."

  - task: "POST /api/admin/import/sheet/sync - Trigger sync (MOCKED)"
    implemented: true
    working: true
    file: "backend/app/routers/admin_import.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "MOCKED. Updates last_sync_at. Returns mock message."

  - task: "Import Service (parse, validate, bulk insert, image download)"
    implemented: true
    working: true
    file: "backend/app/services/import_service.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "parse_excel (CSV+XLSX), validate_hotels, map_columns, create_hotels_bulk (batch 100), download_hotel_images (retry 2x)."

frontend:
  - task: "Admin Import Page (/app/admin/import)"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/admin/AdminImportPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "3 tabs: Excel Yükle, Google Sheets, Import Geçmişi. 5-step wizard for Excel. Column mapping UI. Validation preview. Screenshot verified."

  - task: "Sidebar: DATA & MIGRATION group + Portföy Taşı item"
    implemented: true
    working: "NA"
    file: "frontend/src/components/AppShell.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "New DATA & MIGRATION sidebar group with Portföy Taşı link. minMode=lite (visible in all modes)."

metadata:
  created_by: "main_agent"
  version: "8.0"
  test_sequence: 17
  run_ui: false

test_plan:
  current_focus:
    - "POST /api/admin/import/hotels/upload - Upload CSV/XLSX"
    - "POST /api/admin/import/hotels/validate - Validate with mapping"
    - "POST /api/admin/import/hotels/execute - Bulk import"
    - "GET /api/admin/import/jobs - List import jobs"
    - "GET /api/admin/import/jobs/{job_id} - Job detail + errors"
    - "GET /api/admin/import/export-template - XLSX template download"
    - "POST /api/admin/import/sheet/connect - Google Sheet connection (MOCKED)"
    - "POST /api/admin/import/sheet/sync - Trigger sync (MOCKED)"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"
