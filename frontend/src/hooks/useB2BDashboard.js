/**
 * React Query hook for B2B Dashboard - Sprint 4
 *
 * Provides daily B2B partner/sales data.
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export const b2bDashboardKeys = {
  all: ["b2b-dashboard"],
  today: () => [...b2bDashboardKeys.all, "today"],
};

export function useB2BToday(options = {}) {
  return useQuery({
    queryKey: b2bDashboardKeys.today(),
    queryFn: async () => {
      const { data } = await api.get("/dashboard/b2b-today");
      return data;
    },
    staleTime: 60 * 1000,
    refetchInterval: 90 * 1000,
    ...options,
  });
}
