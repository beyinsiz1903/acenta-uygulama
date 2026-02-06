import { api } from "./api";

export async function fetchB2BEvents(params = {}) {
  const res = await api.get("/b2b/events", { params });
  return res.data;
}
