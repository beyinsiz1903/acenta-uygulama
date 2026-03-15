/**
 * Bookings feature — API layer.
 * All reservation/booking-related API calls.
 */
import { api } from "../../lib/api";

export const bookingsApi = {
  list: async (filters = {}) => {
    const params = {};
    if (filters.status && filters.status !== "all") params.status = filters.status;
    if (filters.q) params.q = filters.q;
    if (filters.page) params.page = String(filters.page);
    if (filters.page_size) params.page_size = String(filters.page_size);
    const { data } = await api.get("/reservations", { params });
    return data;
  },

  detail: async (id) => {
    const { data } = await api.get(`/reservations/${id}`);
    return data;
  },

  reserve: async (payload) => {
    const { data } = await api.post("/reservations/reserve", payload);
    return data;
  },

  confirm: async (id) => {
    const { data } = await api.post(`/reservations/${id}/confirm`);
    return data;
  },

  reject: async (id, reason) => {
    const { data } = await api.post(`/reservations/${id}/reject`, { reason });
    return data;
  },

  cancel: async (id) => {
    const { data } = await api.post(`/reservations/${id}/cancel`);
    return data;
  },

  getProducts: async () => {
    const { data } = await api.get("/products");
    return data;
  },

  getCustomers: async () => {
    const { data } = await api.get("/customers");
    return data;
  },

  getVoucher: async (id) => {
    const resp = await api.get(`/reservations/${id}/voucher`, {
      responseType: "text",
      headers: { Accept: "text/html" },
    });
    return typeof resp.data === "string" ? resp.data : String(resp.data);
  },
};
