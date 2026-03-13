import { api } from "../lib/api";

export const marketLaunchApi = {
  getPilotAgencies: () => api.get("/market-launch/pilot-agencies").then(r => r.data),
  onboardAgency: (data) => api.post("/market-launch/pilot-agencies/onboard", data).then(r => r.data),
  updateAgency: (data) => api.put("/market-launch/pilot-agencies/update", data).then(r => r.data),
  getUsageMetrics: (days = 7) => api.get(`/market-launch/usage-metrics?days=${days}`).then(r => r.data),
  submitFeedback: (data) => api.post("/market-launch/feedback", data).then(r => r.data),
  getFeedback: () => api.get("/market-launch/feedback").then(r => r.data),
  getPricing: () => api.get("/market-launch/pricing").then(r => r.data),
  getLaunchKPIs: () => api.get("/market-launch/launch-kpis").then(r => r.data),
  getLaunchReport: () => api.get("/market-launch/launch-report").then(r => r.data),
  getSupport: () => api.get("/market-launch/support").then(r => r.data),
  getPositioning: () => api.get("/market-launch/positioning").then(r => r.data),
};
