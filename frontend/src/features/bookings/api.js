/**
 * Bookings feature — API layer.
 * All reservation/booking-related API calls.
 */
import { api } from "../../lib/api";

export const bookingsApi = {
  list: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    if (filters.search) params.set("search", filters.search);
    if (filters.page) params.set("page", String(filters.page));
    if (filters.page_size) params.set("page_size", String(filters.page_size));
    const { data } = await api.get(`/reservations?${params.toString()}`);
    return data;
  },

  detail: async (id) => {
    const { data } = await api.get(`/reservations/${id}`);
    return data;
  },

  create: async (payload) => {
    const { data } = await api.post("/reservations", payload);
    return data;
  },

  update: async (id, payload) => {
    const { data } = await api.put(`/reservations/${id}`, payload);
    return data;
  },

  updateStatus: async (id, status) => {
    const { data } = await api.patch(`/reservations/${id}/status`, { status });
    return data;
  },

  cancel: async (id, reason) => {
    const { data } = await api.post(`/reservations/${id}/cancel`, { reason });
    return data;
  },
};
