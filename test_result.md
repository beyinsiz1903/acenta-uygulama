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

user_problem_statement: "GTM Readiness Pack + CRM Pipeline Deepening: demo seed, activation checklist, trial banner, tenant health, CRM stages, move-stage, notes, task complete, automation rules"

backend:
  - task: "Demo Seed POST /api/admin/demo/seed"
    implemented: true
    working: true
    file: "backend/app/routers/gtm_demo_seed.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "VERIFIED: Creates products(3), customers(5), reservations(10), payments(6), deals(5), tasks(10). Idempotent (already_seeded=true). Force mode works."

  - task: "Activation Checklist GET/PUT /api/activation/checklist"
    implemented: true
    working: true
    file: "backend/app/routers/activation_checklist.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "VERIFIED: Auto-creates 7 items, complete item increments count, all_completed tracks correctly."

  - task: "Upgrade Requests POST /api/upgrade-requests"
    implemented: true
    working: true
    file: "backend/app/routers/upgrade_requests.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "VERIFIED: Creates pending request, 409 on duplicate, GET lists requests."

  - task: "Tenant Health GET /api/admin/tenants/health"
    implemented: true
    working: true
    file: "backend/app/routers/tenant_health.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "VERIFIED: Returns tenant health data with filters working."

  - task: "CRM Deal move-stage POST /api/crm/deals/{id}/move-stage"
    implemented: true
    working: true
    file: "backend/app/routers/crm_deals.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "VERIFIED: lead->contacted->proposal->won works. Stage+status sync correctly."

  - task: "CRM Task complete PUT /api/crm/tasks/{id}/complete"
    implemented: true
    working: true
    file: "backend/app/routers/crm_tasks.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "VERIFIED: Marks task as done, audit logged."

  - task: "CRM Notes GET/POST /api/crm/notes"
    implemented: true
    working: true
    file: "backend/app/routers/crm_notes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "VERIFIED: Create and list notes with entity_type/entity_id filtering."

  - task: "Automation Rules (trigger-checks extended)"
    implemented: true
    working: true
    file: "backend/app/services/automation_rules.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "VERIFIED: POST /api/notifications/trigger-checks returns automation_rules results."

frontend:
  - task: "Dashboard with ActivationChecklist + DemoSeedButton + TrialBanner"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/DashboardPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "CRM Pipeline with new stages"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/crm/CrmPipelinePage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

  - task: "Tenant Health Page"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/admin/AdminTenantHealthPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 4
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"
