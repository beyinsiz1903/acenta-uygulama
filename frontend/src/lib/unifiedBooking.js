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

// Revenue & Supplier Optimization APIs
export async function getSupplierRevenueAnalytics(days = 30) {
  const { data } = await api.get(`/revenue/supplier-analytics?days=${days}`);
  return data;
}

export async function getAgencyRevenueAnalytics(days = 30) {
  const { data } = await api.get(`/revenue/agency-analytics?days=${days}`);
  return data;
}

export async function getBusinessKPI(days = 30) {
  const { data } = await api.get(`/revenue/business-kpi?days=${days}`);
  return data;
}

export async function getProfitabilityScores(days = 30) {
  const { data } = await api.get(`/revenue/profitability-scores?days=${days}`);
  return data;
}

export async function getSupplierEconomics(days = 30) {
  const { data } = await api.get(`/revenue/supplier-economics?days=${days}`);
  return data;
}

export async function getCommissionSummary(days = 30) {
  const { data } = await api.get(`/revenue/commission-summary?days=${days}`);
  return data;
}

export async function getMarkupRules() {
  const { data } = await api.get("/revenue/markup-rules");
  return data;
}

export async function upsertMarkupRule(rule) {
  const { data } = await api.post("/revenue/markup-rules", rule);
  return data;
}

export async function deleteMarkupRule(ruleId) {
  const { data } = await api.delete(`/revenue/markup-rules/${ruleId}`);
  return data;
}

export async function calculateMarkup(params) {
  const { data } = await api.post("/revenue/calculate-markup", params);
  return data;
}

export async function getRevenueForecast(months = 3) {
  const { data } = await api.get(`/revenue/forecast?months=${months}`);
  return data;
}

export async function getRevenueAwareSelection(candidates) {
  const { data } = await api.post("/revenue/supplier-selection", candidates);
  return data;
}

export async function getDestinationRevenue(days = 30) {
  const { data } = await api.get(`/revenue/destination-revenue?days=${days}`);
  return data;
}
