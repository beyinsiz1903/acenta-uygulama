/**
 * Reporting feature — API layer.
 * Scheduled reports API calls.
 */
import { api } from "../../lib/api";

export const reportingApi = {
  getSchedules: async () => {
    const { data } = await api.get("/admin/report-schedules");
    return data;
  },

  createSchedule: async (payload) => {
    const { data } = await api.post("/admin/report-schedules", payload);
    return data;
  },

  deleteSchedule: async (id) => {
    const { data } = await api.delete(`/admin/report-schedules/${id}`);
    return data;
  },

  executeDue: async () => {
    const { data } = await api.post("/admin/report-schedules/execute-due");
    return data;
  },
};
