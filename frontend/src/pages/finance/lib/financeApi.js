const API = process.env.REACT_APP_BACKEND_URL;

export async function fetchFinanceOverview() {
  const res = await fetch(`${API}/api/finance/ledger/overview`);
  if (!res.ok) throw new Error("Finance overview fetch failed");
  return res.json();
}

export async function fetchLedgerSummary() {
  const res = await fetch(`${API}/api/finance/ledger/summary`);
  if (!res.ok) throw new Error("Ledger summary fetch failed");
  return res.json();
}

export async function fetchReceivablePayable() {
  const res = await fetch(`${API}/api/finance/ledger/receivable-payable`);
  if (!res.ok) throw new Error("Receivable/payable fetch failed");
  return res.json();
}

export async function fetchRecentPostings(limit = 20) {
  const res = await fetch(`${API}/api/finance/ledger/recent-postings?limit=${limit}`);
  if (!res.ok) throw new Error("Recent postings fetch failed");
  return res.json();
}

export async function fetchLedgerEntries({ skip = 0, limit = 50, account_type, entity_type, financial_status } = {}) {
  const params = new URLSearchParams({ skip, limit });
  if (account_type) params.set("account_type", account_type);
  if (entity_type) params.set("entity_type", entity_type);
  if (financial_status) params.set("financial_status", financial_status);
  const res = await fetch(`${API}/api/finance/ledger/entries?${params}`);
  if (!res.ok) throw new Error("Ledger entries fetch failed");
  return res.json();
}

export async function fetchLedgerEntryDetail(entryId) {
  const res = await fetch(`${API}/api/finance/ledger/entries/${entryId}`);
  if (!res.ok) throw new Error("Ledger entry detail fetch failed");
  return res.json();
}

export async function fetchAgencyBalances({ skip = 0, limit = 50, status } = {}) {
  const params = new URLSearchParams({ skip, limit });
  if (status) params.set("status", status);
  const res = await fetch(`${API}/api/finance/ledger/agency-balances?${params}`);
  if (!res.ok) throw new Error("Agency balances fetch failed");
  return res.json();
}

export async function fetchSupplierPayables({ skip = 0, limit = 50, status } = {}) {
  const params = new URLSearchParams({ skip, limit });
  if (status) params.set("status", status);
  const res = await fetch(`${API}/api/finance/ledger/supplier-payables?${params}`);
  if (!res.ok) throw new Error("Supplier payables fetch failed");
  return res.json();
}

export async function fetchSettlementRuns({ skip = 0, limit = 50, status, run_type } = {}) {
  const params = new URLSearchParams({ skip, limit });
  if (status) params.set("status", status);
  if (run_type) params.set("run_type", run_type);
  const res = await fetch(`${API}/api/finance/settlement-runs?${params}`);
  if (!res.ok) throw new Error("Settlement runs fetch failed");
  return res.json();
}

export async function fetchSettlementRunDetail(runId) {
  const res = await fetch(`${API}/api/finance/settlement-runs/${runId}`);
  if (!res.ok) throw new Error("Settlement run detail fetch failed");
  return res.json();
}

export async function fetchSettlementRunStats() {
  const res = await fetch(`${API}/api/finance/settlement-runs/stats`);
  if (!res.ok) throw new Error("Settlement run stats fetch failed");
  return res.json();
}

export async function fetchReconciliationSummary() {
  const res = await fetch(`${API}/api/finance/reconciliation/summary`);
  if (!res.ok) throw new Error("Reconciliation summary fetch failed");
  return res.json();
}

export async function fetchReconciliationSnapshots({ skip = 0, limit = 20, status } = {}) {
  const params = new URLSearchParams({ skip, limit });
  if (status) params.set("status", status);
  const res = await fetch(`${API}/api/finance/reconciliation/snapshots?${params}`);
  if (!res.ok) throw new Error("Reconciliation snapshots fetch failed");
  return res.json();
}

export async function fetchMarginRevenueSummary() {
  const res = await fetch(`${API}/api/finance/reconciliation/margin-revenue`);
  if (!res.ok) throw new Error("Margin revenue summary fetch failed");
  return res.json();
}

export async function seedFinanceData() {
  const res = await fetch(`${API}/api/finance/ledger/seed`, { method: "POST" });
  if (!res.ok) throw new Error("Seed finance data failed");
  return res.json();
}

// ── Phase 2B: Workflow & Ops ──

export async function createSettlementDraft(data) {
  const res = await fetch(`${API}/api/finance/settlement-runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Create settlement draft failed");
  return res.json();
}

export async function submitSettlement(runId, actor = "admin") {
  const res = await fetch(`${API}/api/finance/settlement-runs/${runId}/submit`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Submit failed");
  }
  return res.json();
}

export async function approveSettlement(runId, actor = "admin", reason = "") {
  const res = await fetch(`${API}/api/finance/settlement-runs/${runId}/approve`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor, reason }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Approve failed");
  }
  return res.json();
}

export async function rejectSettlement(runId, actor = "admin", reason = "") {
  const res = await fetch(`${API}/api/finance/settlement-runs/${runId}/reject`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor, reason }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Reject failed");
  }
  return res.json();
}

export async function markPaidSettlement(runId, actor = "admin") {
  const res = await fetch(`${API}/api/finance/settlement-runs/${runId}/mark-paid`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Mark paid failed");
  }
  return res.json();
}

export async function addEntriesToDraft(runId, entryIds) {
  const res = await fetch(`${API}/api/finance/settlement-runs/${runId}/add-entries`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entry_ids: entryIds }),
  });
  if (!res.ok) throw new Error("Add entries failed");
  return res.json();
}

export async function removeEntryFromDraft(runId, entryId) {
  const res = await fetch(`${API}/api/finance/settlement-runs/${runId}/remove-entry/${entryId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Remove entry failed");
  return res.json();
}

export async function fetchUnassignedEntries({ entity_type, entity_id, limit = 100 } = {}) {
  const params = new URLSearchParams();
  if (entity_type) params.set("entity_type", entity_type);
  if (entity_id) params.set("entity_id", entity_id);
  if (limit) params.set("limit", limit);
  const res = await fetch(`${API}/api/finance/settlement-runs/unassigned-entries?${params}`);
  if (!res.ok) throw new Error("Unassigned entries fetch failed");
  return res.json();
}

export async function fetchExceptions({ skip = 0, limit = 50, status, severity, exception_type } = {}) {
  const params = new URLSearchParams({ skip, limit });
  if (status) params.set("status", status);
  if (severity) params.set("severity", severity);
  if (exception_type) params.set("exception_type", exception_type);
  const res = await fetch(`${API}/api/finance/exceptions?${params}`);
  if (!res.ok) throw new Error("Exceptions fetch failed");
  return res.json();
}

export async function fetchExceptionStats() {
  const res = await fetch(`${API}/api/finance/exceptions/stats`);
  if (!res.ok) throw new Error("Exception stats fetch failed");
  return res.json();
}

export async function resolveException(exceptionId, data) {
  const res = await fetch(`${API}/api/finance/exceptions/${exceptionId}/resolve`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Resolve failed");
  }
  return res.json();
}

export async function dismissException(exceptionId, reason = "") {
  const res = await fetch(`${API}/api/finance/exceptions/${exceptionId}/dismiss`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Dismiss failed");
  }
  return res.json();
}
