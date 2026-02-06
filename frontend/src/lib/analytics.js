import { api } from "./api";

export async function fetchRevenueSummary(params = {}) {
  const res = await api.get("/admin/analytics/revenue-summary", { params });
  return res.data;
}

export async function fetchUsageOverview(params = {}) {
  const res = await api.get("/admin/analytics/usage-overview", { params });
  return res.data;
}
