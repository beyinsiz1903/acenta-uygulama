/**
 * Analytics feature — API layer.
 * Reporting, KPI analytics, supplier economics API calls.
 */
import { api } from "../../lib/api";

export const analyticsApi = {
  getKPIAnalytics: async (filters = {}) => {
    const { data } = await api.get("/analytics/kpi", { params: filters });
    return data;
  },

  getSupplierEconomics: async () => {
    const { data } = await api.get("/analytics/supplier-economics");
    return data;
  },

  getRevenueOptimization: async () => {
    const { data } = await api.get("/analytics/revenue-optimization");
    return data;
  },

  getReconciliation: async (filters = {}) => {
    const { data } = await api.get("/analytics/reconciliation", { params: filters });
    return data;
  },

  getReports: async (filters = {}) => {
    const { data } = await api.get("/reports", { params: filters });
    return data;
  },
};
