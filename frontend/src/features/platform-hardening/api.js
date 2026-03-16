/**
 * Platform Hardening — API layer + reusable data hook.
 */
import { useState, useEffect, useCallback } from "react";
import { api } from "../../lib/api";

export function useHardeningApi(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(path);
      setData(res.data);
    } catch { /* silent */ }
    setLoading(false);
  }, [path]);
  useEffect(() => { fetch_(); }, [fetch_]);
  return { data, loading, refetch: fetch_ };
}

export const hardeningApi = {
  startPhase: (phaseId) => api.post(`/hardening/execution/phase/${phaseId}/start`),
  completeTask: (phaseId, taskId) => api.post(`/hardening/execution/phase/${phaseId}/task/${taskId}/complete`),
  resolveBlocker: (blockerId) => api.post(`/hardening/execution/blocker/${blockerId}/resolve`),
  runSimulation: (endpoint) => api.post(endpoint),
  runIncident: (type) => api.post(`/hardening/activation/incident/${type}`),
};
