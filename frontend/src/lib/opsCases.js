import { api, apiErrorMessage } from "./api";

export async function listOpsGuestCases(params = {}) {
  const res = await api.get("/ops/guest-cases/", { params });
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
