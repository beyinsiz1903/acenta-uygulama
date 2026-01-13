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

export async function getPublicBookingSummary({ org, booking_code }) {
  const res = await api.get(`/public/bookings/by-code/${booking_code}`, { params: { org } });
  return res.data;
}

export async function requestMyBookingLink(body) {
  // Backend expects snake_case fields: booking_code, email
  const res = await api.post("/public/my-booking/request-link", body);
  return res.data;
}

export { apiErrorMessage };
