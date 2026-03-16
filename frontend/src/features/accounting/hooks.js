/**
 * Accounting feature — TanStack Query hooks.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { accountingApi } from "./api";

export const accountingKeys = {
  all: ["accounting"],
  dashboard: () => [...accountingKeys.all, "dashboard"],
  syncJobs: (filters) => [...accountingKeys.all, "sync-jobs", filters],
  rules: () => [...accountingKeys.all, "rules"],
  customers: (filters) => [...accountingKeys.all, "customers", filters],
  credentials: () => [...accountingKeys.all, "credentials"],
  providers: () => [...accountingKeys.all, "providers"],
};

export function useAccountingDashboard(options = {}) {
  return useQuery({
    queryKey: accountingKeys.dashboard(),
    queryFn: accountingApi.getDashboard,
    staleTime: 30_000,
    ...options,
  });
}

export function useSyncJobs(filters = {}, options = {}) {
  return useQuery({
    queryKey: accountingKeys.syncJobs(filters),
    queryFn: () => accountingApi.getSyncJobs(filters),
    staleTime: 15_000,
    select: (data) => data?.items || [],
    ...options,
  });
}

export function useRetryJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: accountingApi.retryJob,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountingKeys.all });
    },
  });
}

export function useAccountingRules(options = {}) {
  return useQuery({
    queryKey: accountingKeys.rules(),
    queryFn: accountingApi.getRules,
    staleTime: 30_000,
    select: (data) => data?.rules || [],
    ...options,
  });
}

export function useAccountingCustomers(filters = {}, options = {}) {
  return useQuery({
    queryKey: accountingKeys.customers(filters),
    queryFn: () => accountingApi.getCustomers(filters),
    staleTime: 30_000,
    ...options,
  });
}
