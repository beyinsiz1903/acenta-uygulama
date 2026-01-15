import { api, apiErrorMessage } from "./api";

export async function listOpsCases(params = {}) {
  const res = await api.get("/ops/cases/", { params });
  return res.data;
}

export async function listOpsCasesForBooking(bookingId) {
  if (!bookingId) return { items: [], page: 1, page_size: 20, total: 0 };
  const res = await api.get("/ops/cases/", { params: { booking_id: bookingId } });
  return res.data;
}

export async function getOpsCase(caseId) {
  const res = await api.get(`/ops/cases/${caseId}`);
  return res.data;
}

export async function closeOpsCase(caseId, note) {
  const res = await api.post(`/ops/cases/${caseId}/close`, { note });
  return res.data;
}

export async function createOpsCase(body) {
  const res = await api.post("/ops/cases/", body);
  return res.data;
}

export async function updateOpsCase(caseId, body) {
  const res = await api.patch(`/ops/cases/${caseId}`, body);
  return res.data;
}

export { apiErrorMessage };
