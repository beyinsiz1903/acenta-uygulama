import { api } from "./api";

export async function fetchAuditLogs(params = {}) {
  const res = await api.get("/admin/audit-logs", { params });
  return res.data;
}
