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

user_problem_statement: "GTM Readiness Pack (demo seed, activation checklist, upgrade requests, tenant health) + CRM Pipeline Deepening (new stages, move-stage, complete task, notes, automation rules)"

backend:
  - task: "Demo Seed (POST /api/admin/demo/seed)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/gtm_demo_seed.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "New endpoint for 1-click demo data seeding. Supports mode (light/full), with_finance, with_crm params. Idempotent via demo_seed_runs collection. Rate limited."

  - task: "Activation Checklist (GET/PUT /api/activation/checklist)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/activation_checklist.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Checklist with 7 items, auto-created on onboarding complete. PUT to mark items complete. Audit logged."

  - task: "Upgrade Requests (POST /api/upgrade-requests)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/upgrade_requests.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Tenant admin can request upgrade. Super admin can change plan directly. Notifications created for admins."

  - task: "Tenant Health (GET /api/admin/tenants/health)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/tenant_health.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Super admin only. Returns per-tenant health metrics with filters (trial_expiring, inactive, overdue)."

  - task: "CRM Deal Move Stage (POST /api/crm/deals/{id}/move-stage)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/crm_deals.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "New stages: lead, contacted, proposal, won, lost. Audit logged. CRM event fired."

  - task: "CRM Task Complete (PUT /api/crm/tasks/{id}/complete)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/crm_tasks.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Mark task as done. Audit logged."

  - task: "CRM Notes (GET/POST /api/crm/notes)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/crm_notes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Notes attachable to customer/deal/reservation/payment. Audit logged."

  - task: "Automation Rules (overdue payment + deal proposal)"
    implemented: true
    working: "NA"
    file: "backend/app/services/automation_rules.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Two rules: overdue payment task creation + deal proposal overdue notification. Idempotent per day via rule_runs collection. Triggered via /api/notifications/trigger-checks."

frontend:
  - task: "Dashboard with Demo Seed + Activation Checklist"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/DashboardPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Demo seed button + activation checklist widget added to dashboard."

  - task: "Trial Banner + Upgrade CTA"
    implemented: true
    working: "NA"
    file: "frontend/src/components/TrialBanner.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Trial banner in AppShell, upgrade modal with plan selection."

  - task: "Tenant Health Page"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/admin/AdminTenantHealthPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Admin page with tenant health table and filters."

  - task: "CRM Pipeline (new stages)"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/crm/CrmPipelinePage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Updated to new stages: lead, contacted, proposal, won, lost. moveDealStage API used."

  - task: "Sidebar Navigation Update"
    implemented: true
    working: "NA"
    file: "frontend/src/components/AppShell.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added Tenant Health under YÖNETİM section."

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 3
  run_ui: false

test_plan:
  current_focus: 
    - "Demo Seed (POST /api/admin/demo/seed)"
    - "Activation Checklist (GET/PUT /api/activation/checklist)"
    - "Upgrade Requests (POST /api/upgrade-requests)"
    - "Tenant Health (GET /api/admin/tenants/health)"
    - "CRM Deal Move Stage (POST /api/crm/deals/{id}/move-stage)"
    - "CRM Task Complete (PUT /api/crm/tasks/{id}/complete)"
    - "CRM Notes (GET/POST /api/crm/notes)"
    - "Automation Rules (overdue payment + deal proposal)"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"
