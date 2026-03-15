/**
 * CRM feature — API layer.
 * Customer, task, event, pipeline API calls.
 */
import { api } from "../../lib/api";

export const crmApi = {
  getCustomers: async (filters = {}) => {
    const { data } = await api.get("/crm/customers", { params: filters });
    return data;
  },

  getCustomerDetail: async (id) => {
    const { data } = await api.get(`/crm/customers/${id}`);
    return data;
  },

  createCustomer: async (payload) => {
    const { data } = await api.post("/crm/customers", payload);
    return data;
  },

  updateCustomer: async (id, payload) => {
    const { data } = await api.put(`/crm/customers/${id}`, payload);
    return data;
  },

  deleteCustomer: async (id) => {
    const { data } = await api.delete(`/crm/customers/${id}`);
    return data;
  },

  getTasks: async (filters = {}) => {
    const { data } = await api.get("/crm/tasks", { params: filters });
    return data;
  },

  getEvents: async (filters = {}) => {
    const { data } = await api.get("/crm/events", { params: filters });
    return data;
  },

  getPipeline: async () => {
    const { data } = await api.get("/crm/pipeline");
    return data;
  },

  getDuplicates: async () => {
    const { data } = await api.get("/crm/duplicates");
    return data;
  },
};
