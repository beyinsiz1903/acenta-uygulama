/**
 * Finance feature — TanStack Query hooks.
 */
import { useQuery } from "@tanstack/react-query";
import { financeApi } from "./api";

export const financeKeys = {
  all: ["finance"],
  refunds: (filters) => [...financeKeys.all, "refunds", filters],
  exposure: () => [...financeKeys.all, "exposure"],
  settlements: (filters) => [...financeKeys.all, "settlements", filters],
  settlementRuns: (filters) => [...financeKeys.all, "settlement-runs", filters],
  settlementRunDetail: (id) => [...financeKeys.all, "settlement-runs", id],
  supplierAccruals: () => [...financeKeys.all, "supplier-accruals"],
};

export function useRefunds(filters = {}, options = {}) {
  return useQuery({
    queryKey: financeKeys.refunds(filters),
    queryFn: () => financeApi.getRefunds(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useFinanceExposure(options = {}) {
  return useQuery({
    queryKey: financeKeys.exposure(),
    queryFn: financeApi.getExposure,
    staleTime: 60_000,
    ...options,
  });
}

export function useSettlements(filters = {}, options = {}) {
  return useQuery({
    queryKey: financeKeys.settlements(filters),
    queryFn: () => financeApi.getSettlements(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useSettlementRuns(filters = {}, options = {}) {
  return useQuery({
    queryKey: financeKeys.settlementRuns(filters),
    queryFn: () => financeApi.getSettlementRuns(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useSettlementRunDetail(id, options = {}) {
  return useQuery({
    queryKey: financeKeys.settlementRunDetail(id),
    queryFn: () => financeApi.getSettlementRunDetail(id),
    enabled: !!id,
    staleTime: 30_000,
    ...options,
  });
}
