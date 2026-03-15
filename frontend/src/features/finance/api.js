/**
 * Finance feature — API layer.
 * Settlements, refunds, exposure, billing API calls.
 */
import { api } from "../../lib/api";

export const financeApi = {
  getRefunds: async (filters = {}) => {
    const { data } = await api.get("/finance/refunds", { params: filters });
    return data;
  },

  getExposure: async () => {
    const { data } = await api.get("/finance/exposure");
    return data;
  },

  getSettlements: async (filters = {}) => {
    const { data } = await api.get("/settlements", { params: filters });
    return data;
  },

  getSettlementRuns: async (filters = {}) => {
    const { data } = await api.get("/settlements/runs", { params: filters });
    return data;
  },

  getSettlementRunDetail: async (id) => {
    const { data } = await api.get(`/settlements/runs/${id}`);
    return data;
  },

  getSupplierAccruals: async () => {
    const { data } = await api.get("/finance/supplier-accruals");
    return data;
  },
};
