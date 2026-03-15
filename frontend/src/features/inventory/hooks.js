/**
 * Inventory feature — TanStack Query hooks.
 * New hooks wrapping the inventory API layer.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { inventoryApi } from "./api";

export const inventoryKeys = {
  all: ["inventory"],
  sync: () => [...inventoryKeys.all, "sync"],
  syncStatus: () => [...inventoryKeys.sync(), "status"],
  syncJobs: (filters) => [...inventoryKeys.sync(), "jobs", filters],
  search: (query) => [...inventoryKeys.all, "search", query],
  stats: () => [...inventoryKeys.all, "stats"],
  supplierConfig: () => [...inventoryKeys.all, "supplier-config"],
  supplierMetrics: () => [...inventoryKeys.all, "supplier-metrics"],
  supplierHealth: () => [...inventoryKeys.all, "supplier-health"],
  kpiDrift: () => [...inventoryKeys.all, "kpi-drift"],
};

export function useInventorySyncStatus(options = {}) {
  return useQuery({
    queryKey: inventoryKeys.syncStatus(),
    queryFn: inventoryApi.getSyncStatus,
    staleTime: 10_000,
    ...options,
  });
}

export function useInventorySyncJobs(filters = {}, options = {}) {
  return useQuery({
    queryKey: inventoryKeys.syncJobs(filters),
    queryFn: () => inventoryApi.getSyncJobs(filters),
    staleTime: 15_000,
    ...options,
  });
}

export function useInventorySearch(query = {}, options = {}) {
  return useQuery({
    queryKey: inventoryKeys.search(query),
    queryFn: () => inventoryApi.search(query),
    staleTime: 30_000,
    enabled: Object.keys(query).length > 0,
    ...options,
  });
}

export function useInventoryStats(options = {}) {
  return useQuery({
    queryKey: inventoryKeys.stats(),
    queryFn: inventoryApi.getStats,
    staleTime: 60_000,
    ...options,
  });
}

export function useSupplierConfig(options = {}) {
  return useQuery({
    queryKey: inventoryKeys.supplierConfig(),
    queryFn: inventoryApi.getSupplierConfig,
    staleTime: 60_000,
    ...options,
  });
}

export function useSupplierHealth(options = {}) {
  return useQuery({
    queryKey: inventoryKeys.supplierHealth(),
    queryFn: inventoryApi.getSupplierHealth,
    staleTime: 30_000,
    ...options,
  });
}

export function useKPIDrift(options = {}) {
  return useQuery({
    queryKey: inventoryKeys.kpiDrift(),
    queryFn: inventoryApi.getKPIDrift,
    staleTime: 60_000,
    ...options,
  });
}

export function useTriggerSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: inventoryApi.triggerSync,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.sync() });
      queryClient.invalidateQueries({ queryKey: inventoryKeys.stats() });
    },
  });
}

export function useRevalidateInventory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: inventoryApi.revalidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.all });
    },
  });
}

export function useSetSupplierConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: inventoryApi.setSupplierConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.supplierConfig() });
    },
  });
}

export function useDeleteSupplierConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: inventoryApi.deleteSupplierConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.supplierConfig() });
    },
  });
}

export function useValidateSandbox() {
  return useMutation({
    mutationFn: inventoryApi.validateSandbox,
  });
}
