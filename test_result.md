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

user_problem_statement: "Feature modules: E-Fatura Layer, SMS Notification Layer, QR Ticket + Check-in. All with provider abstraction, mock providers, tenant isolation, RBAC, audit logging, idempotency."

backend:
  - task: "A) E-Fatura - Profile CRUD"
    implemented: true
    working: "NA"
    file: "backend/app/routers/efatura.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "PUT/GET /api/efatura/profile. Tenant-scoped, admin-only."

  - task: "A) E-Fatura - Invoice CRUD + Send + Cancel"
    implemented: true
    working: "NA"
    file: "backend/app/routers/efatura.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "POST/GET /api/efatura/invoices, POST send/cancel. Idempotent. MockProvider. Audit logged."

  - task: "B) SMS Notification - Send + Bulk + Logs"
    implemented: true
    working: "NA"
    file: "backend/app/routers/sms_notifications.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "POST /api/sms/send, /api/sms/send-bulk, GET /api/sms/logs, /api/sms/templates. MockProvider."

  - task: "C) QR Ticket - Create + Check-in + Cancel + Stats"
    implemented: true
    working: "NA"
    file: "backend/app/routers/tickets.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "POST /api/tickets, /api/tickets/check-in, /api/tickets/{code}/cancel, GET stats. Idempotent per reservation. Audit logged."

metadata:
  created_by: "main_agent"
  version: "4.0"
  test_sequence: 7
  run_ui: false

test_plan:
  current_focus:
    - "A) E-Fatura - Profile CRUD"
    - "A) E-Fatura - Invoice CRUD + Send + Cancel"
    - "B) SMS Notification - Send + Bulk + Logs"
    - "C) QR Ticket - Create + Check-in + Cancel + Stats"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"
