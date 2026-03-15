/**
 * Analytics feature — TanStack Query hooks.
 */
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "./api";

export const analyticsKeys = {
  all: ["analytics"],
  kpi: (filters) => [...analyticsKeys.all, "kpi", filters],
  supplierEconomics: () => [...analyticsKeys.all, "supplier-economics"],
  revenueOptimization: () => [...analyticsKeys.all, "revenue-optimization"],
  reconciliation: (filters) => [...analyticsKeys.all, "reconciliation", filters],
  reports: (filters) => [...analyticsKeys.all, "reports", filters],
};

export function useKPIAnalytics(filters = {}, options = {}) {
  return useQuery({
    queryKey: analyticsKeys.kpi(filters),
    queryFn: () => analyticsApi.getKPIAnalytics(filters),
    staleTime: 60_000,
    ...options,
  });
}

export function useSupplierEconomics(options = {}) {
  return useQuery({
    queryKey: analyticsKeys.supplierEconomics(),
    queryFn: analyticsApi.getSupplierEconomics,
    staleTime: 60_000,
    ...options,
  });
}

export function useRevenueOptimization(options = {}) {
  return useQuery({
    queryKey: analyticsKeys.revenueOptimization(),
    queryFn: analyticsApi.getRevenueOptimization,
    staleTime: 60_000,
    ...options,
  });
}
