import { api } from "./api";

export async function fetchRevenueSummary(params = {}) {
  const res = await api.get("/admin/analytics/revenue-summary", { params });
  return res.data;
}

export async function fetchUsageOverview(params = {}) {
  const res = await api.get("/admin/analytics/usage-overview", { params });
  return res.data;
}

export async function fetchPushStatus() {
  const res = await api.get("/admin/billing/push-status");
  return res.data;
}

export async function fetchCronStatus() {
  const res = await api.get("/admin/billing/cron-status");
  return res.data;
}
