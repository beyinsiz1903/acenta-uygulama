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

user_problem_statement: "Enterprise Hardening Sprint E1-E4: Governance (RBAC v2, Approval Workflow, Immutable Audit), Security (2FA TOTP, IP Whitelist, Password Policy), Observability (Structured Logging, Health Endpoints, Rate Limiting), Enterprise UX (White-Label, Full Data Export, Scheduled Reports)"

backend:
  - task: "E3.2 Health Endpoints (live + ready)"
    implemented: true
    working: true
    file: "backend/app/routers/enterprise_health.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Verified: /api/health/live returns alive, /api/health/ready returns ready with DB check"

  - task: "E2.3 Password Policy"
    implemented: true
    working: true
    file: "backend/app/services/password_policy.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Verified: weak password returns 400 with violations list, strong password accepted"

  - task: "E3.3 Rate Limiting (login, signup, export, approvals)"
    implemented: true
    working: true
    file: "backend/app/middleware/rate_limit_middleware.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Verified: returns 429 when exceeding limits"

  - task: "E3.1 Structured JSON Logging"
    implemented: true
    working: true
    file: "backend/app/middleware/structured_logging_middleware.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Logs request_id, tenant_id, user_id, path, method, status_code, latency_ms. X-Request-Id header added."

  - task: "E1.1 Granular RBAC v2"
    implemented: true
    working: "NA"
    file: "backend/app/routers/enterprise_rbac.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Seed, list, upsert permissions/roles endpoints implemented. Additive - backward compat."

  - task: "E1.2 Approval Workflow Engine"
    implemented: true
    working: "NA"
    file: "backend/app/routers/enterprise_approvals.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Create, list, approve, reject endpoints. Double-approve blocked (409). Audit logged."

  - task: "E1.3 Immutable Audit Log (hash chain + CSV export)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/enterprise_audit.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Per-tenant hash chain. Verify integrity. Streaming CSV export."

  - task: "E2.1 2FA (TOTP) with recovery codes"
    implemented: true
    working: "NA"
    file: "backend/app/routers/enterprise_2fa.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Enable, verify, disable endpoints. Login flow checks 2FA. Recovery codes supported."

  - task: "E2.2 Tenant IP Whitelist"
    implemented: true
    working: "NA"
    file: "backend/app/routers/enterprise_ip_whitelist.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Middleware checks allowed_ips in tenant settings. Admin CRUD for whitelist."

  - task: "E4.1 White-Label Settings"
    implemented: true
    working: "NA"
    file: "backend/app/routers/enterprise_whitelabel.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Extended existing whitelabel with logo_url, primary_color, company_name."

  - task: "E4.2 Full Data Export (zip)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/enterprise_export.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "POST /api/admin/tenant/export returns zip with customers, deals, tasks, reservations, payments JSON."

  - task: "E4.3 Scheduled Reports"
    implemented: true
    working: "NA"
    file: "backend/app/routers/enterprise_schedules.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "CRUD for schedules. APScheduler runs every 15 min. Manual execute-due endpoint."

frontend:
  - task: "E4.1 White-Label UI (dynamic logo/color/name)"
    implemented: false
    working: "NA"
    file: "frontend/src/components/AppShell.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true

metadata:
  created_by: "main_agent"
  version: "3.0"
  test_sequence: 5
  run_ui: false

test_plan:
  current_focus:
    - "E1.1 Granular RBAC v2"
    - "E1.2 Approval Workflow Engine"
    - "E1.3 Immutable Audit Log (hash chain + CSV export)"
    - "E2.1 2FA (TOTP) with recovery codes"
    - "E2.2 Tenant IP Whitelist"
    - "E4.2 Full Data Export (zip)"
    - "E4.3 Scheduled Reports"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"
