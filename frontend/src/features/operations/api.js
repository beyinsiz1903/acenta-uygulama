/**
 * Operations feature — API layer.
 * Guest cases, ops tasks, incidents API calls.
 */
import { api } from "../../lib/api";

export const operationsApi = {
  getGuestCases: async (filters = {}) => {
    const { data } = await api.get("/ops/guest-cases", { params: filters });
    return data;
  },

  getGuestCaseDetail: async (id) => {
    const { data } = await api.get(`/ops/guest-cases/${id}`);
    return data;
  },

  getOpsTasks: async (filters = {}) => {
    const { data } = await api.get("/ops/tasks", { params: filters });
    return data;
  },

  getIncidents: async (filters = {}) => {
    const { data } = await api.get("/ops/incidents", { params: filters });
    return data;
  },

  getBookingDetail: async (bookingId) => {
    const { data } = await api.get(`/ops/bookings/${bookingId}`);
    return data;
  },
};
