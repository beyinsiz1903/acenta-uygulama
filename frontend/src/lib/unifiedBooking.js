import { api } from "./api";

// Unified Booking API helpers
export async function unifiedSearch(params) {
  const { data } = await api.post("/unified-booking/search", params);
  return data;
}

export async function revalidatePrice(params) {
  const { data } = await api.post("/unified-booking/revalidate", params);
  return data;
}

export async function executeBooking(params) {
  const { data } = await api.post("/unified-booking/book", params);
  return data;
}

export async function getRegistry() {
  const { data } = await api.get("/unified-booking/registry");
  return data;
}

export async function getBookingMetrics() {
  const { data } = await api.get("/unified-booking/metrics");
  return data;
}

export async function getOrgAudit() {
  const { data } = await api.get("/unified-booking/audit");
  return data;
}

export async function getBookingAudit(bookingId) {
  const { data } = await api.get(`/unified-booking/audit/${bookingId}`);
  return data;
}

export async function getReconciliation(bookingId) {
  const { data } = await api.get(`/unified-booking/reconciliation/${bookingId}`);
  return data;
}

export async function getReconciliationMismatches() {
  const { data } = await api.get("/unified-booking/reconciliation-mismatches");
  return data;
}
