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

user_problem_statement: "Enterprise SaaS core: Self-Service Onboarding (Phase 5), WebPOS + Internal Ledger (Phase 6), Notifications Engine (Phase 8), Advanced Reporting (Phase 7), System Hardening (Phase 9)"

backend:
  - task: "Signup API (POST /api/onboarding/signup)"
    implemented: true
    working: true
    file: "backend/app/routers/onboarding.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "2-step signup creates org+tenant+user, trial subscription, capabilities, onboarding_state. Returns JWT."

  - task: "Onboarding Wizard (state, steps, complete)"
    implemented: true
    working: true
    file: "backend/app/routers/onboarding.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "GET state, PUT steps/company|product|invite|partner, POST complete all working."

  - task: "WebPOS Payments (record, list, refund)"
    implemented: true
    working: true
    file: "backend/app/routers/webpos.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Record payment, list, refund, partial refund, daily-summary all working."

  - task: "WebPOS Ledger (append-only, balance)"
    implemented: true
    working: true
    file: "backend/app/services/webpos_service.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Append-only ledger, auto balance_after, debit on payment, credit on refund."

  - task: "Notifications CRUD"
    implemented: true
    working: true
    file: "backend/app/routers/notifications.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "List, unread-count, mark-read, mark-all-read with tenant isolation."

  - task: "Advanced Reports (financial-summary, product-performance, partner-performance, aging)"
    implemented: true
    working: true
    file: "backend/app/routers/advanced_reports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "All date-range parameterized, snapshot-safe."

frontend:
  - task: "Signup Page (/signup)"
    implemented: true
    working: true
    file: "frontend/src/pages/public/SignupPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Screenshot verified."

  - task: "Pricing Page (/pricing)"
    implemented: true
    working: true
    file: "frontend/src/pages/public/PricingPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Screenshot verified."

  - task: "WebPOS Page (/app/finance/webpos)"
    implemented: true
    working: true
    file: "frontend/src/pages/WebPOSPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Payment modal, refund, ledger view, balance."

  - task: "Advanced Reports Page (/app/reports)"
    implemented: true
    working: true
    file: "frontend/src/pages/AdvancedReportsPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "4 sections + CSV export."

  - task: "NotificationBell"
    implemented: true
    working: true
    file: "frontend/src/components/NotificationBell.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Bell with unread badge, dropdown, mark-all-read."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "Signup API"
    - "WebPOS Payments"
    - "Notifications CRUD"
    - "Advanced Reports"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"
