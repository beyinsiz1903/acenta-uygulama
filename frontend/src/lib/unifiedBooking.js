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

// Intelligence APIs
export async function getSearchSuggestions(productType = "hotel") {
  const { data } = await api.get(`/intelligence/suggestions?product_type=${productType}`);
  return data;
}

export async function getConversionFunnel(days = 30) {
  const { data } = await api.get(`/intelligence/funnel?days=${days}`);
  return data;
}

export async function getDailyStats(days = 30) {
  const { data } = await api.get(`/intelligence/daily-stats?days=${days}`);
  return data;
}

export async function getSupplierScores(days = 30) {
  const { data } = await api.get(`/intelligence/supplier-scores?days=${days}`);
  return data;
}

export async function getSupplierRecommendations() {
  const { data } = await api.get("/intelligence/supplier-recommendations");
  return data;
}

export async function getSupplierRevenue(days = 30) {
  const { data } = await api.get(`/intelligence/supplier-revenue?days=${days}`);
  return data;
}

export async function trackFunnelEvent(eventType, details = {}) {
  const { data } = await api.post("/intelligence/track", { event_type: eventType, details });
  return data;
}

export async function getKPISummary(days = 30) {
  const { data } = await api.get(`/intelligence/kpi-summary?days=${days}`);
  return data;
}
