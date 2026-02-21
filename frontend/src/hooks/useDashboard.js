/**
 * React Query hooks for dashboard data.
 *
 * Provides:
 * - useDashboardKPI: KPI statistics (sales, reservations, conversion)
 * - useDashboardReservationWidgets: Completed/pending/abandoned reservations
 * - useDashboardWeeklySummary: Weekly summary table
 * - useDashboardPopularProducts: Popular products carousel
 * - useDashboardRecentCustomers: Latest customers
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

// Query keys namespace
export const dashboardKeys = {
  all: ["dashboard"],
  kpi: () => [...dashboardKeys.all, "kpi"],
  widgets: () => [...dashboardKeys.all, "widgets"],
  weekly: () => [...dashboardKeys.all, "weekly"],
  popular: () => [...dashboardKeys.all, "popular"],
  customers: () => [...dashboardKeys.all, "customers"],
};

export function useDashboardKPI(options = {}) {
  return useQuery({
    queryKey: dashboardKeys.kpi(),
    queryFn: async () => {
      const { data } = await api.get("/dashboard/kpi-stats");
      return data;
    },
    staleTime: 60 * 1000, // 1 min
    ...options,
  });
}

export function useDashboardReservationWidgets(options = {}) {
  return useQuery({
    queryKey: dashboardKeys.widgets(),
    queryFn: async () => {
      const { data } = await api.get("/dashboard/reservation-widgets");
      return data;
    },
    staleTime: 60 * 1000,
    ...options,
  });
}

export function useDashboardWeeklySummary(options = {}) {
  return useQuery({
    queryKey: dashboardKeys.weekly(),
    queryFn: async () => {
      const { data } = await api.get("/dashboard/weekly-summary");
      return data;
    },
    staleTime: 60 * 1000,
    ...options,
  });
}

export function useDashboardPopularProducts(options = {}) {
  return useQuery({
    queryKey: dashboardKeys.popular(),
    queryFn: async () => {
      const { data } = await api.get("/dashboard/popular-products");
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 min
    ...options,
  });
}

export function useDashboardRecentCustomers(options = {}) {
  return useQuery({
    queryKey: dashboardKeys.customers(),
    queryFn: async () => {
      const { data } = await api.get("/dashboard/recent-customers");
      return data;
    },
    staleTime: 2 * 60 * 1000, // 2 min
    ...options,
  });
}
