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

user_problem_statement: "Operational Excellence Layer: O1) Backup & Restore, O2) Data Integrity Monitoring, O3) Monitoring & Metrics, O4) Disaster Readiness, O5) SLA / Uptime Tracking"

backend:
  - task: "O1 - Backup System (list/run/delete)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/admin_system_backups.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET/POST/DELETE /api/admin/system/backups. Uses mongodump subprocess. Retention cleanup via APScheduler cron at 04:00."

  - task: "O2 - Integrity Report (audit chain, ledger, orphans)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/admin_system_integrity.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/admin/system/integrity-report. Checks audit chain per-tenant, ledger integrity, orphan records. Daily APScheduler cron at 03:00."

  - task: "O3 - System Metrics"
    implemented: true
    working: "NA"
    file: "backend/app/routers/admin_system_metrics.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/system/metrics. Returns active_tenants, total_users, invoices_today, sms_sent_today, tickets_checked_in_today, avg_request_latency_ms, error_rate_percent, disk_usage_percent."

  - task: "O3 - System Errors (aggregated)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/admin_system_errors.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/admin/system/errors. Lists aggregated system errors. Slow requests (>1000ms) and unhandled exceptions auto-aggregated via middleware."

  - task: "O4 - Enhanced Health Ready"
    implemented: true
    working: "NA"
    file: "backend/app/routers/enterprise_health.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/health/ready checks Mongo ping, APScheduler, disk >10%, error rate <10%. Returns 503 on critical fail."

  - task: "O4 - Maintenance Mode"
    implemented: true
    working: "NA"
    file: "backend/app/routers/admin_maintenance.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "PATCH /api/admin/tenant/maintenance toggles maintenance_mode on organization. GET /api/admin/tenant/maintenance returns status."

  - task: "O5 - Uptime Tracking"
    implemented: true
    working: "NA"
    file: "backend/app/routers/admin_system_uptime.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/admin/system/uptime?days=30. APScheduler checks every minute. Returns uptime_percent, total_minutes, downtime_minutes."

  - task: "O5 - Incident Tracking (CRUD)"
    implemented: true
    working: "NA"
    file: "backend/app/routers/admin_system_incidents.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET/POST /api/admin/system/incidents, PATCH /api/admin/system/incidents/{id}/resolve. Audit logged."

frontend:
  - task: "O1 - System Backups Page"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/admin/AdminSystemBackupsPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Table view, run backup, delete backup. Route: /app/admin/system-backups"

  - task: "O2 - System Integrity Page"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/admin/AdminSystemIntegrityPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Integrity report with audit chain, ledger, orphan sections. Route: /app/admin/system-integrity"

  - task: "O3 - System Metrics Page"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/admin/AdminSystemMetricsPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Metric cards for all system metrics. Route: /app/admin/system-metrics"

  - task: "O3 - System Errors Page"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/admin/AdminSystemErrorsPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Error list with severity filter, stack traces. Route: /app/admin/system-errors"

  - task: "O5 - System Uptime Page"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/admin/AdminSystemUptimePage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Big uptime percentage display with period selector. Route: /app/admin/system-uptime"

  - task: "O5 - System Incidents Page"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/admin/AdminSystemIncidentsPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Incident list, create, resolve flow. Route: /app/admin/system-incidents"

metadata:
  created_by: "main_agent"
  version: "6.0"
  test_sequence: 10
  run_ui: false

test_plan:
  current_focus:
    - "O1 - Backup System (list/run/delete)"
    - "O2 - Integrity Report (audit chain, ledger, orphans)"
    - "O3 - System Metrics"
    - "O3 - System Errors (aggregated)"
    - "O4 - Enhanced Health Ready"
    - "O4 - Maintenance Mode"
    - "O5 - Uptime Tracking"
    - "O5 - Incident Tracking (CRUD)"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"
