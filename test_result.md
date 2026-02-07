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

user_problem_statement: "Segmented Product Modes Architecture: Implement lite/pro/enterprise visibility layer for multi-tenant SaaS ERP. Mode stored in tenant_settings (tenant-scoped). Backend capabilities stay intact — only UI surface changes."

backend:
  - task: "GET /api/system/product-mode - tenant self-read"
    implemented: true
    working: true
    file: "backend/app/routers/system_product_mode.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Returns product_mode, visible_nav_groups, hidden_nav_items, label_overrides. Default enterprise. Tested via curl."

  - task: "GET /api/admin/tenants/{tenant_id}/product-mode - admin read"
    implemented: true
    working: true
    file: "backend/app/routers/admin_product_mode.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Returns tenant mode + available_modes list + visibility config. Requires super_admin role."

  - task: "PATCH /api/admin/tenants/{tenant_id}/product-mode - mode switch with audit"
    implemented: true
    working: true
    file: "backend/app/routers/admin_product_mode.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Changes tenant mode, writes audit log, returns diff. Tested lite->pro->enterprise transitions."

  - task: "GET /api/admin/tenants/{tenant_id}/product-mode-preview - diff preview"
    implemented: true
    working: true
    file: "backend/app/routers/admin_product_mode.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Shows newly_visible and newly_hidden items for target mode switch. Tested all transitions."

  - task: "Product Modes Config (constants/product_modes.py)"
    implemented: true
    working: true
    file: "backend/app/constants/product_modes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "MODE_VISIBILITY config for lite/pro/enterprise. is_at_least(), get_mode_diff(), get_hidden_items_for_mode()."

  - task: "TenantSettingsRepository (tenant_settings collection)"
    implemented: true
    working: true
    file: "backend/app/repositories/tenant_settings_repository.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "CRUD for tenant_settings. get_product_mode defaults to enterprise. set_product_mode with upsert."

frontend:
  - task: "ProductModeContext + Provider"
    implemented: true
    working: "NA"
    file: "frontend/src/contexts/ProductModeContext.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Fetches /api/system/product-mode. Caches in localStorage (5min). Provides mode, isAtLeast(), refresh()."

  - task: "IfMode component"
    implemented: true
    working: "NA"
    file: "frontend/src/components/IfMode.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "<IfMode atLeast='pro'>, <IfMode exact='lite'>, <IfMode not='lite'>. Conditional render."

  - task: "Sidebar mode-aware filtering"
    implemented: true
    working: "NA"
    file: "frontend/src/components/AppShell.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "ADMIN_GROUPED_NAV items have minMode + modeKey. filterNavByMode filters by mode level + server hidden items list."

  - task: "Admin Product Mode Settings Page"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/admin/AdminProductModePage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "3 mode cards (Lite/Pro/Enterprise), current mode badge, preview modal with diff, confirm+apply. Route: /app/admin/product-mode"

metadata:
  created_by: "main_agent"
  version: "7.0"
  test_sequence: 12
  run_ui: false

test_plan:
  current_focus:
    - "GET /api/system/product-mode - tenant self-read"
    - "PATCH /api/admin/tenants/{tenant_id}/product-mode - mode switch with audit"
    - "GET /api/admin/tenants/{tenant_id}/product-mode-preview - diff preview"
    - "GET /api/admin/tenants/{tenant_id}/product-mode - admin read"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"
