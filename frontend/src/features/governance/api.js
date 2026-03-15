/**
 * Governance feature — API layer.
 * Audit logs, approvals, action policies API calls.
 */
import { api } from "../../lib/api";

export const governanceApi = {
  getAuditLogs: async (filters = {}) => {
    const { data } = await api.get("/audit-logs", { params: filters });
    return data;
  },

  getApprovals: async (filters = {}) => {
    const { data } = await api.get("/approvals", { params: filters });
    return data;
  },

  approveRequest: async (id) => {
    const { data } = await api.post(`/approvals/${id}/approve`);
    return data;
  },

  rejectRequest: async (id, reason) => {
    const { data } = await api.post(`/approvals/${id}/reject`, { reason });
    return data;
  },

  getActionPolicies: async () => {
    const { data } = await api.get("/action-policies");
    return data;
  },

  // Admin users management
  getAllUsers: async () => {
    const { data } = await api.get("/admin/all-users");
    return data || [];
  },

  getAgenciesList: async () => {
    const { data } = await api.get("/admin/agencies");
    return data || [];
  },
};
