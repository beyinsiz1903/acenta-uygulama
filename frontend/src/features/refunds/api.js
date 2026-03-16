/**
 * Refunds feature — API layer.
 * All refund-related API calls for finance operations.
 */
import { api } from "../../lib/api";

export const refundsApi = {
  /* ─── List / Detail ─── */
  list: async ({ status, limit } = {}) => {
    const params = {};
    if (status === "open") params.status = "open,pending_approval";
    else if (status === "closed") params.status = "closed";
    if (limit) params.limit = limit;
    const { data } = await api.get("/ops/finance/refunds", { params });
    return data;
  },

  detail: async (caseId) => {
    const { data } = await api.get(`/ops/finance/refunds/${caseId}`);
    return data;
  },

  bookingFinancials: async (bookingId) => {
    const { data } = await api.get(`/ops/bookings/${bookingId}/financials`);
    return data;
  },

  bookingRefundHistory: async (bookingId) => {
    const { data } = await api.get("/ops/finance/refunds", {
      params: { booking_id: bookingId, status: "closed", limit: 5 },
    });
    return data;
  },

  /* ─── Approval Flow ─── */
  approveStep1: async (caseId, approvedAmount) => {
    const { data } = await api.post(`/ops/finance/refunds/${caseId}/approve-step1`, {
      approved_amount: approvedAmount,
    });
    return data;
  },

  approveStep2: async (caseId, note) => {
    const { data } = await api.post(`/ops/finance/refunds/${caseId}/approve-step2`, {
      note: note || null,
    });
    return data;
  },

  reject: async (caseId, reason) => {
    const { data } = await api.post(`/ops/finance/refunds/${caseId}/reject`, {
      reason: reason || null,
    });
    return data;
  },

  markPaid: async (caseId, paymentReference) => {
    const { data } = await api.post(`/ops/finance/refunds/${caseId}/mark-paid`, {
      payment_reference: paymentReference,
    });
    return data;
  },

  close: async (caseId, note) => {
    const { data } = await api.post(`/ops/finance/refunds/${caseId}/close`, {
      note: note || null,
    });
    return data;
  },

  /* ─── Documents ─── */
  listDocuments: async (caseId) => {
    const { data } = await api.get("/ops/documents", {
      params: { entity_type: "refund_case", entity_id: caseId },
    });
    return data;
  },

  uploadDocument: async (caseId, { file, tag, note }) => {
    const formData = new FormData();
    formData.append("entity_type", "refund_case");
    formData.append("entity_id", caseId);
    formData.append("tag", tag);
    if (note) formData.append("note", note);
    formData.append("file", file);
    const { data } = await api.post("/ops/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  deleteDocument: async (documentId) => {
    const { data } = await api.delete(`/ops/documents/${documentId}`, { data: {} });
    return data;
  },

  downloadDocument: async (documentId) => {
    const resp = await api.get(`/ops/documents/${documentId}/download`, {
      responseType: "blob",
    });
    return resp.data;
  },

  /* ─── Tasks ─── */
  listTasks: async (caseId) => {
    const { data } = await api.get(`/ops/refunds/${caseId}/tasks`);
    return data;
  },

  createTask: async (body) => {
    const { data } = await api.post("/ops/tasks", body);
    return data;
  },

  updateTask: async (taskId, patch) => {
    const { data } = await api.patch(`/ops/tasks/${taskId}`, patch);
    return data;
  },
};
