import { api, apiErrorMessage } from "./api";

export async function searchPublic(params = {}) {
  const res = await api.get("/public/search", { params });
  return res.data;
}

export { apiErrorMessage };
