import { api } from "../lib/api";

export const scalabilityApi = {
  getCacheStats: () => api.get("/scalability/cache-stats").then(r => r.data),
  getRateLimitStats: () => api.get("/scalability/rate-limit-stats").then(r => r.data),
  getSchedulerStatus: () => api.get("/scalability/scheduler-status").then(r => r.data),
  triggerJob: (jobName) => api.post("/scalability/scheduler/trigger", { job_name: jobName }).then(r => r.data),
  getSupplierMetrics: () => api.get("/scalability/supplier-metrics").then(r => r.data),
  getSearchMetrics: () => api.get("/scalability/search-metrics").then(r => r.data),
  getRedisHealth: () => api.get("/scalability/redis-health").then(r => r.data),
  getMonitoringDashboard: () => api.get("/scalability/monitoring-dashboard").then(r => r.data),
  getPrometheusMetrics: () => api.get("/scalability/metrics").then(r => r.data),
};
