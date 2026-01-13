import { api, apiErrorMessage } from "./api";

export async function searchPublic(params = {}) {
  const res = await api.get("/public/search", { params });
  return res.data;
}

export async function createPublicQuote(body) {
  const res = await api.post("/public/quote", body);
  return res.data;
}

export async function createPublicCheckout(body) {
  const res = await api.post("/public/checkout", body);
  return res.data;
}

export { apiErrorMessage };
