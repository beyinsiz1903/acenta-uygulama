/**
 * Dashboard feature — API layer.
 * All dashboard-related API calls.
 */
import { api } from "../../lib/api";

export const dashboardApi = {
  getKPI: async () => {
    const { data } = await api.get("/dashboard/kpi-stats");
    return data;
  },

  getReservationWidgets: async () => {
    const { data } = await api.get("/dashboard/reservation-widgets");
    return data;
  },

  getWeeklySummary: async () => {
    const { data } = await api.get("/dashboard/weekly-summary");
    return data;
  },

  getPopularProducts: async () => {
    const { data } = await api.get("/dashboard/popular-products");
    return data;
  },

  getRecentCustomers: async () => {
    const { data } = await api.get("/dashboard/recent-customers");
    return data;
  },
};
