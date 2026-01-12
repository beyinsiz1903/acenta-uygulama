import { api, apiErrorMessage } from "./api";

export async function listOpsGuestCases(params = {}) {
  const res = await api.get("/ops/guest-cases/", { params });
  return res.data;
}

export async function listOpsGuestCasesForBooking(bookingId) {
  if (!bookingId) return { items: [], page: 1, page_size: 20, total: 0 };
  const res = await api.get("/ops/guest-cases/", { params: { booking_id: bookingId } });
  return res.data;
}

export async function getOpsGuestCase(caseId) {
  const res = await api.get(`/ops/guest-cases/${caseId}`);
  return res.data;
}

export async function closeOpsGuestCase(caseId, note) {
  const res = await api.post(`/ops/guest-cases/${caseId}/close`, { note });
  return res.data;
}

export { apiErrorMessage };
