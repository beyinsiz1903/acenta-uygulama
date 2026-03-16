/**
 * Platform Hardening — API layer + reusable data hook.
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";

export function useHardeningApi(path) {
  const { data = null, isLoading: loading, refetch } = useQuery({
    queryKey: ["hardening", path],
    queryFn: async () => {
      const res = await api.get(path);
      return res.data;
    },
    staleTime: 30_000,
  });
  return { data, loading, refetch };
}

export const hardeningApi = {
  startPhase: (phaseId) => api.post(`/hardening/execution/phase/${phaseId}/start`),
  completeTask: (phaseId, taskId) => api.post(`/hardening/execution/phase/${phaseId}/task/${taskId}/complete`),
  resolveBlocker: (blockerId) => api.post(`/hardening/execution/blocker/${blockerId}/resolve`),
  runSimulation: (endpoint) => api.post(endpoint),
  runIncident: (type) => api.post(`/hardening/activation/incident/${type}`),
};
