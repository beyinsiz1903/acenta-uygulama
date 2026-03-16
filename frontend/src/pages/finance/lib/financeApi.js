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
