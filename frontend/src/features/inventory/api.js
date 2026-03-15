/**
 * Inventory feature — API layer.
 * All inventory sync, search, and supplier-related API calls.
 */
import { api } from "../../lib/api";

export const inventoryApi = {
  triggerSync: async (params = {}) => {
    const { data } = await api.post("/inventory/sync/trigger", params);
    return data;
  },

  getSyncStatus: async () => {
    const { data } = await api.get("/inventory/sync/status");
    return data;
  },

  getSyncJobs: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.limit) params.set("limit", String(filters.limit));
    if (filters.status) params.set("status", filters.status);
    const { data } = await api.get(`/inventory/sync/jobs?${params.toString()}`);
    return data;
  },

  search: async (query = {}) => {
    const { data } = await api.get("/inventory/search", { params: query });
    return data;
  },

  getStats: async () => {
    const { data } = await api.get("/inventory/stats");
    return data;
  },

  revalidate: async (hotelId) => {
    const { data } = await api.post("/inventory/revalidate", { hotel_id: hotelId });
    return data;
  },

  getSupplierConfig: async () => {
    const { data } = await api.get("/inventory/supplier-config");
    return data;
  },

  setSupplierConfig: async (config) => {
    const { data } = await api.post("/inventory/supplier-config", config);
    return data;
  },

  deleteSupplierConfig: async (supplier) => {
    const { data } = await api.delete(`/inventory/supplier-config/${supplier}`);
    return data;
  },

  validateSandbox: async (supplier) => {
    const { data } = await api.post("/inventory/sandbox/validate", { supplier });
    return data;
  },

  getSupplierMetrics: async () => {
    const { data } = await api.get("/inventory/supplier-metrics");
    return data;
  },

  getSupplierHealth: async () => {
    const { data } = await api.get("/inventory/supplier-health");
    return data;
  },

  getKPIDrift: async () => {
    const { data } = await api.get("/inventory/kpi/drift");
    return data;
  },
};
