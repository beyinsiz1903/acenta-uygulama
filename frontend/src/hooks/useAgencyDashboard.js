/**
 * React Query hook for Agency Dashboard - Sprint 2
 *
 * Provides task-oriented daily overview data for agency users.
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export const agencyDashboardKeys = {
  all: ["agency-dashboard"],
  today: () => [...agencyDashboardKeys.all, "today"],
};

export function useAgencyToday(options = {}) {
  return useQuery({
    queryKey: agencyDashboardKeys.today(),
    queryFn: async () => {
      const { data } = await api.get("/dashboard/agency-today");
      return data;
    },
    staleTime: 30 * 1000, // 30 sec — agency dashboard refreshes often
    refetchInterval: 60 * 1000, // auto-refresh every minute
    ...options,
  });
}
