import { api } from "../lib/api";

export const operationsApi = {
  validateSupplier: (supplierCode) => api.post("/operations/validate-supplier", { supplier_code: supplierCode }).then(r => r.data),
  validateAll: () => api.post("/operations/validate-all").then(r => r.data),
  getCapabilityMatrix: () => api.get("/operations/capability-matrix").then(r => r.data),
  getSupplierSLA: () => api.get("/operations/supplier-sla").then(r => r.data),
  cacheBurstTest: (burstCount = 5) => api.post("/operations/cache-burst-test", { burst_count: burstCount }).then(r => r.data),
  rateLimitTest: (supplierCode = "ratehawk", count = 10) => api.post("/operations/rate-limit-test", { supplier_code: supplierCode, request_count: count }).then(r => r.data),
  fallbackTest: () => api.get("/operations/fallback-test").then(r => r.data),
  reconciliationTest: () => api.get("/operations/reconciliation-test").then(r => r.data),
  monitoringTest: () => api.get("/operations/monitoring-test").then(r => r.data),
  getLaunchReadiness: () => api.get("/operations/launch-readiness").then(r => r.data),
  getOnboardingChecklist: () => api.get("/operations/onboarding-checklist").then(r => r.data),
};
