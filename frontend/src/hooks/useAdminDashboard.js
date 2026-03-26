/**
 * React Query hook for Admin Dashboard - Sprint 3
 *
 * Provides executive overview data for admin/super_admin users.
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export const adminDashboardKeys = {
  all: ["admin-dashboard"],
  today: () => [...adminDashboardKeys.all, "today"],
};

export function useAdminToday(options = {}) {
  return useQuery({
    queryKey: adminDashboardKeys.today(),
    queryFn: async () => {
      const { data } = await api.get("/dashboard/admin-today");
      return data;
    },
    staleTime: 60 * 1000,
    refetchInterval: 90 * 1000,
    ...options,
  });
}
