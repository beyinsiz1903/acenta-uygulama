/**
 * Accounting feature — API layer.
 * Sync jobs, credentials, rules, customers.
 */
import { api } from "../../lib/api";

export const accountingApi = {
  getDashboard: async () => {
    const { data } = await api.get("/accounting/dashboard");
    return data;
  },

  getSyncJobs: async (filters = {}) => {
    const { data } = await api.get("/accounting/sync-jobs", { params: { limit: 100, ...filters } });
    return data;
  },

  retryJob: async (jobId) => {
    const { data } = await api.post("/accounting/retry", { job_id: jobId });
    return data;
  },

  getProviders: async () => {
    const { data } = await api.get("/accounting/providers");
    return data;
  },

  getCredentials: async () => {
    const { data } = await api.get("/accounting/credentials");
    return data;
  },

  saveCredentials: async (payload) => {
    const { data } = await api.post("/accounting/credentials", payload);
    return data;
  },

  testConnection: async (provider) => {
    const { data } = await api.post("/accounting/test-connection", { provider });
    return data;
  },

  deleteCredentials: async (provider) => {
    const { data } = await api.delete(`/accounting/credentials/${provider}`);
    return data;
  },

  getRules: async () => {
    const { data } = await api.get("/accounting/rules");
    return data;
  },

  createRule: async (payload) => {
    const { data } = await api.post("/accounting/rules", payload);
    return data;
  },

  updateRule: async ({ ruleId, payload }) => {
    const { data } = await api.put(`/accounting/rules/${ruleId}`, payload);
    return data;
  },

  deleteRule: async (ruleId) => {
    const { data } = await api.delete(`/accounting/rules/${ruleId}`);
    return data;
  },

  getCustomers: async (filters = {}) => {
    const { data } = await api.get("/accounting/customers", { params: { limit: 50, ...filters } });
    return data;
  },
};
